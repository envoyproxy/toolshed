import "version" as version;
import "ansi" as ansi;

def to_date_string(datestring):
  # `YYYY-MM-DDTHH:MM:SS[.fff][Z|+HH:MM]` (NVD omits the zone, CVE Program
  # records may carry an offset) to the UTC date
  datestring
  | if . == null then "unknown"
    else
      sub("\\.[0-9]+"; "")
      | capture("^(?<base>[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2})"
                + "(?:Z|(?<sign>[+-])(?<hh>[0-9]{2}):?(?<mm>[0-9]{2}))?$")
      | ((.base + "Z") | fromdateiso8601)
        - (if .sign == null then 0
           else (if .sign == "-" then -1 else 1 end)
                * (((.hh // "0") | tonumber) * 3600 + ((.mm // "0") | tonumber) * 60)
           end)
      | strftime("%Y-%m-%d")
    end;

def deps_list(deps):
  [deps | to_entries[] | {name: .key} + .value];

def match_cpe_tag_version(cpe_version; dep_version):
  cpe_version == "*"
  or version::eq(version::parse(cpe_version); dep_version);

def matching_cpe_tags(cpe; dep):
  cpe as $cpe
  | dep as $dep
  | ($dep.cpes // [$dep.cpe])[]
  | select($cpe.vendor == .vendor
           and $cpe.product == .product
           and match_cpe_tag_version($cpe.version; $dep.version));

def match_cpe_tag(cpe; dep):
  any(matching_cpe_tags(cpe; dep); true);

def parse_cpe_versions(versions):
  {end_inc: version::parse(versions.end_inc),
   end_exc: version::parse(versions.end_exc),
   start_inc: version::parse(versions.start_inc),
   start_exc: version::parse(versions.start_exc)};

def match_cpe_version(cpe; dep):
  parse_cpe_versions(cpe.versions) as $v
  | ($v.start_inc != null and version::lt(dep.version; $v.start_inc))
    or ($v.start_exc != null and version::lte(dep.version; $v.start_exc))
    or ($v.end_inc != null and version::gt(dep.version; $v.end_inc))
    or ($v.end_exc != null and version::gte(dep.version; $v.end_exc))
  | not;

def updated_since_cve(cpe; dep):
  dep.release_date > to_date_string(cpe.published);

def match_dep_cpe(cpe; dep):
  match_cpe_tag(cpe.cpe; dep)
  and match_cpe_version(cpe; dep)
  and (updated_since_cve(cpe; dep) | not);

def matching_deps(cpes; deps):
  [cpes[]? as $cpe
   | deps[] as $dep
   | select(match_dep_cpe($cpe; $dep))
   | {cpe: $cpe, dep: $dep}];

def parse_cpe_tag(cpe):
  cpe | split(":")
  | {part: (.[2] // "*"),
     vendor: (.[3] // "*"),
     product: (.[4] // "*"),
     version: (.[5] // "*")};

def pre_parse_cpe_versions(cpe):
  {end_inc: cpe.versionEndIncluding,
   end_exc: cpe.versionEndExcluding,
   start_inc: cpe.versionStartIncluding,
   start_exc: cpe.versionStartExcluding};

def parse_cve_cpe(cpe; cve):
  {cpe: parse_cpe_tag(cpe.criteria),
   versions: pre_parse_cpe_versions(cpe),
   published: cve.cve.published};

def get_severity(metrics):
  if metrics.cvssMetricV31 then metrics.cvssMetricV31[0].cvssData.baseSeverity
  elif metrics.cvssMetricV30 then metrics.cvssMetricV30[0].cvssData.baseSeverity
  else "UNKNOWN" end;

def github_name(dep):
  # (owner, repo) from the first github url in the dependency metadata, if any
  [((dep.urls // []) + [dep.project_url // empty, dep.license_url // empty])[]
   | capture("^https?://github\\.com/(?<vendor>[^/]+)/(?<product>[^/]+)")?
   | .product |= sub("\\.git$"; "")]
  | first // empty;

def dep_names(dep; cpes):
  # candidate (vendor, product) pairs for matching CNA-asserted vendor/product:
  # the CPE tags, the same with any `_project` vendor suffix removed, and the
  # github owner/repo
  [cpes[] | {vendor, product}, {vendor: (.vendor | sub("_project$"; "")), product}]
  + [github_name(dep)]
  | map({vendor: (.vendor | ascii_downcase), product: (.product | ascii_downcase)})
  | unique;

def parse_deps(deps):
  deps
  | with_entries(
      (.value.cpe | if type == "array" then . else [.] end
       | map(select(. != null and . != "N/A"))) as $tags
      | select($tags | length > 0)
      | .value = (.value |
          [$tags[] | {match: .} + parse_cpe_tag(.)] as $cpes
          | {release_date,
             version: version::parse(.version),
             cpe: $cpes[0],
             cpes: $cpes,
             names: dep_names(.; $cpes)}));

def iterate_cves(cves; deps; ignored):
  [cves[]
   | . as $cve
   | select(ignored | index($cve.cve.id) | not)
   | [.cve.configurations[]?.nodes[]?.cpeMatch[]?
      # `vulnerable: false` marks an environment the vulnerable product runs
      # on or with, not something that is itself affected
      | select(.vulnerable != false)
      | parse_cve_cpe(.; $cve)]
   | matching_deps(.; deps)
   | select(length > 0)
   | {id: $cve.cve.id, matched: ., cve: $cve.cve}];

# Both arguments have jq --slurpfile shape; dependencies are already parsed.
def scan($deps; $ignored):
  deps_list($deps[0]) as $dependencies
  | iterate_cves(.vulnerabilities; $dependencies; $ignored[0]);

def analyzed_ids(cves):
  # ids of NVD records that carry (non-empty) CPE configurations
  [cves[] | select(((.cve.configurations // []) | length) > 0) | .cve.id];

# As `scan`, also listing the analyzed ids, so one pass over the NVD data
# serves both the matches and the CNA precedence check.
def nvd_scan($deps; $ignored):
  {matches: scan($deps; $ignored),
   analyzed: analyzed_ids(.vulnerabilities)};

# CVE Program (cvelistV5) records, as compacted by `dependency/cve:cvelist_fetch`:
# `{id, assigner, published, descriptions, metrics, affected}`, where `affected`
# holds the CNA and ADP `affected[]` entries. These carry the affected versions
# asserted on publication, so they cover CVEs that NVD has not (yet) analyzed.

def cna_tighter_bound(current; candidate; lower):
  # keep the tighter of two bounds on the same side: the larger lower
  # bound, the smaller upper bound
  if current == null then candidate
  elif lower then
    (if version::gt(version::parse(candidate); version::parse(current)) then candidate else current end)
  else
    (if version::lt(version::parse(candidate); version::parse(current)) then candidate else current end)
  end;

def cna_version_text(text):
  # free-text constraints as used by eg the GitHub CNA: `< 1.34.7`, `>= 2.0, < 2.1.3`;
  # repeated bounds intersect
  reduce (text | split(",")[] | gsub("^\\s+|\\s+$"; "")) as $constraint ({};
    (($constraint | capture("^(?<op>>=|<=|>|<|=)?\\s*(?<version>\\S+)$")?) // null) as $m
    | if $m == null then .invalid = true
      elif $m.op == "<" then .end_exc = cna_tighter_bound(.end_exc; $m.version; false)
      elif $m.op == "<=" then .end_inc = cna_tighter_bound(.end_inc; $m.version; false)
      elif $m.op == ">" then .start_exc = cna_tighter_bound(.start_exc; $m.version; true)
      elif $m.op == ">=" then .start_inc = cna_tighter_bound(.start_inc; $m.version; true)
      else .exact = $m.version
      end);

def cna_wildcard(limit):
  (limit | type) == "string" and (limit | test("\\.\\*$"));

def cna_wildcard_limit(limit):
  # a trailing `.*` on a limit means the rest of that series, eg `2.5.*`:
  # everything below `2.6.0-0`, the lowest pre-release of the next series,
  # so that `2.6.0-rc.1` is outside it too. A series that cannot be resolved
  # (`3.x.*`) is null, so the entry is ignored rather than string-compared.
  limit as $limit
  | if cna_wildcard($limit) then
      ($limit | sub("\\.\\*$"; "") | split("."))
      | try ((.[-1] |= ((tonumber + 1) | tostring)) + ["0", "0"] | .[0:3] | join(".") + "-0") catch null
    else $limit end;

def cna_git_revision(entry):
  # a single commit, rather than a range of them
  entry.lessThan == null and entry.lessThanOrEqual == null
  and ((entry.version // "") | test("^[0-9a-f]{7,64}$"));

def cna_versions(entry):
  # normalize a CNA `versions[]` entry to the start/end bounds used for NVD
  # cpe matching, `{exact}` for a single version or `{revision}` for a single
  # git commit; git (commit) ranges cannot be compared and are ignored
  (if entry.versionType == "git" then
     (if cna_git_revision(entry) then {revision: entry.version} else {invalid: true} end)
   elif entry.lessThan != null then
     {start_inc: entry.version, end_exc: cna_wildcard_limit(entry.lessThan)}
   elif cna_wildcard(entry.lessThanOrEqual) then
     # up to and including the whole series: below the next one
     {start_inc: entry.version, end_exc: cna_wildcard_limit(entry.lessThanOrEqual)}
   elif entry.lessThanOrEqual != null then
     {start_inc: entry.version, end_inc: entry.lessThanOrEqual}
   else
     cna_version_text(entry.version // "*")
   end)
  # `*`/`unspecified` are unbounded, as is `0` as a range start; an
  # unresolved (null) bound makes the entry unusable
  | with_entries(select(.value != "*" and .value != "unspecified"))
  | with_entries(select((.key == "start_inc" and .value == "0") | not))
  | if any(.[]; . == null) then {invalid: true} else . end;

def match_cna_version(versions; dep):
  # whether the dep version is covered by the normalized versions
  versions as $v
  | if $v.invalid then false
    # a commit is compared literally: as a version, `0000007` equals `7.0.0`
    elif $v.revision != null then dep.version.string == $v.revision
    elif $v.exact != null then version::eq(dep.version; version::parse($v.exact))
    else match_cpe_version({versions: $v}; dep)
    end;

def cna_entry_status(entry; dep):
  # the entry's status for the dep version, after any `changes[]` at or
  # below that version (the last such change wins)
  reduce (entry.changes[]? | select(.at != null and .status != null)
          | select(version::lte(version::parse(.at); dep.version))) as $change
    (null;
     if . == null or version::gt(version::parse($change.at); version::parse(.at))
     then $change else . end)
  | (.status // entry.status);

def cna_covering(affected; dep):
  # the `versions[]` entries covering the dep version, in order, with the
  # effective status
  [affected.versions[]? as $entry
   | cna_versions($entry) as $v
   | select($v.invalid | not)
   | select(match_cna_version($v; dep))
   | {status: cna_entry_status($entry; dep)}];

def match_cna_affected_version(affected; dep):
  # as the CVE record format: the first entry covering the version decides
  # (after its `changes[]`), `defaultStatus` applies when none does
  cna_covering(affected; dep)
  | if length == 0 then affected.defaultStatus == "affected"
    else .[0].status == "affected" end;

def match_cna_name(affected; dep):
  # match on the entry's cpes where given (including any cpe version),
  # otherwise on vendor/product
  if (affected.cpes // []) != [] then
    any(affected.cpes[]; match_cpe_tag(parse_cpe_tag(.); dep))
  else
    {vendor: ((affected.vendor // "") | ascii_downcase),
     product: ((affected.product // "") | ascii_downcase)} as $name
    | $name.product != ""
      and any(dep.names[]; . == $name)
  end;

def match_dep_cna(affected; cve; dep):
  match_cna_name(affected; dep)
  and (cve.published == null or (updated_since_cve({published: cve.published}; dep) | not))
  and match_cna_affected_version(affected; dep);

def cna_name_key(vendor; product):
  "\((vendor // "") | ascii_downcase)/\((product // "") | ascii_downcase)";

def cna_dep_index(deps):
  # deps by candidate `vendor/product` name, for O(1) lookup per affected
  # entry, plus the deps to try for entries matched on `cpes`
  {names: (reduce deps[] as $dep ({};
             reduce $dep.names[] as $name (.;
               .[cna_name_key($name.vendor; $name.product)] += [$dep]))),
   cpes: [deps[] | select((.cpes // []) != [])]};

def cna_candidate_deps(affected; index):
  if (affected.cpes // []) != [] then index.cpes[]
  else (index.names[cna_name_key(affected.vendor; affected.product)] // [])[]
  end;

def matching_cna_deps(affected; cve; index):
  # `index` is `cna_dep_index(deps)`
  [affected[] as $affected
   | cna_candidate_deps($affected; index) as $dep
   | select(match_dep_cna($affected; cve; $dep))
   | {affected: $affected, dep: $dep}];

def get_cna_severity(cve):
  # the highest cvss version with a severity, across all metrics entries
  [cve.metrics[]?] as $metrics
  | [("cvssV4_0", "cvssV3_1", "cvssV3_0") as $key
     | $metrics[] | .[$key]? | .baseSeverity? // empty]
  | first // "UNKNOWN";

def iterate_cna_cves(cves; deps; ignored):
  cna_dep_index(deps) as $index
  | [cves[]
     | . as $cve
     | select(ignored | index($cve.id) | not)
     | matching_cna_deps($cve.affected; $cve; $index)
     | select(length > 0)
     | {id: $cve.id, matched: ., cve: $cve}];

# As `scan`, over cvelist records (`.records`).
def scan_cna($deps; $ignored):
  deps_list($deps[0]) as $dependencies
  | iterate_cna_cves(.records; $dependencies; $ignored[0]);

def nvd_dependency(cve; match):
  "Dep: \(ansi::green)\(ansi::bold)\(match.dep.name)@\(match.dep.version.string)\(ansi::reset) \(ansi::green)(\(match.dep.release_date)\(ansi::reset))

  Source: NVD
  Severity: \(get_severity(cve.metrics))
  Published: \(to_date_string(cve.published))
  CPE: \(first(matching_cpe_tags(match.cpe.cpe; match.dep)).match // "")
  Version: \(match.cpe.cpe.version)
  Start (including/excluding): \(match.cpe.versions.start_inc // "")/\(match.cpe.versions.start_exc // "")
  End (including/excluding): \(match.cpe.versions.end_inc // "")/\(match.cpe.versions.end_exc // "")
";

def cna_bounds_string(versions):
  # the normalized bounds of a `versions[]` entry, as `a <= v < b`
  versions as $v
  | if $v.invalid then "(unparsed)"
    elif $v.revision != null then "commit \($v.revision)"
    elif $v.exact != null then "v = \($v.exact)"
    else
      ([if $v.start_inc then "\($v.start_inc) <=" elif $v.start_exc then "\($v.start_exc) <" else empty end]
       + ["v"]
       + [if $v.end_exc then "< \($v.end_exc)" elif $v.end_inc then "<= \($v.end_inc)" else empty end])
      | if length == 1 then "all" else join(" ") end
    end;

def cna_version_strings(affected):
  # every `versions[]` entry with its bounds, status and any changes, and
  # the default, so what the report shows is what was matched against
  ([affected.versions[]?
    | "\(cna_bounds_string(cna_versions(.))) \(.status // "unknown")"
      + ([.changes[]? | " then \(.status) at \(.at)"] | join(""))]
   + (if affected.defaultStatus != null then ["default \(affected.defaultStatus)"] else [] end))
  | if length == 0 then "(no versions)" else join("; ") end;

def nvd_state(cve):
  # how NVD stands on a CVE matched from its CVE Program record
  if cve.nvd_analyzed == true then "analyzed, no CPE match for the tracked tags"
  elif cve.nvd_analyzed == false then "not analyzed (no CPE data)"
  else "unknown" end;

def cna_dependency(cve; match):
  "Dep: \(ansi::green)\(ansi::bold)\(match.dep.name)@\(match.dep.version.string)\(ansi::reset) \(ansi::green)(\(match.dep.release_date)\(ansi::reset))

  Source: CVE Program (\(cve.assigner // "unknown CNA"))
  Severity: \(get_cna_severity(cve))
  Published: \(to_date_string(cve.published))
  Affected: \(match.affected.vendor // "")/\(match.affected.product // "") \(cna_version_strings(match.affected))
  CPEs: \((match.affected.cpes // []) | join(", "))
";

def matched_dependency(cve; match):
  (if match.source == "cna" then cna_dependency(cve.cna; match)
   else nvd_dependency(cve.cve; match) end)
  + "
  ---------------------------------

  \((cve.cve // cve.cna).descriptions[0].value)

  ";

def matched_dependencies(cve):
  cve as $cve
  | [cve.matched[] | matched_dependency($cve; .)]
  | join("");

def cve_header(cve):
  "================ \(ansi::red)\(ansi::bold)\(ansi::underline)\(cve.id)\(ansi::reset) ================"
  + (if cve.nvd_analyzed != null then "
  NVD: \(nvd_state(cve))" else "" end);

def cve_report(cve):
  "\(cve_header(cve))
  \(matched_dependencies(cve))
  ";

def summary(matches):
  ([matches[] | select(.sources == ["cna"])] | length) as $cna_only
  | ([matches[] | select(.sources == ["nvd"])] | length) as $nvd_only
  | ([matches[] | select((.sources // []) | length > 1)] | length) as $both
  | "
  ==========================================
  \(ansi::red)\(ansi::bold)\(matches | length) potential CVE vulnerabilities found\(ansi::reset)"
    + (if ($cna_only + $both) > 0
       then " (\($nvd_only) NVD only, \($cna_only) CVE Program only, \($both) both)"
       else "" end);

def report(matches):
  matches as $matches
  | (matches | map(cve_report(.)) | join("\n")) + summary($matches);

# Merge NVD and CVE Program matches by id, tagging the sources.
#   nvd: `{matches, analyzed}` from `nvd_scan`
#   cna: `scan_cna` matches
# The result keeps `cve` (the NVD record where there is one, else the CVE
# Program record), `cna` (the CVE Program record), `sources`, and for
# records only matched from the CVE Program whether NVD has analyzed them.
def merge_sources(nvd; cna):
  nvd.matches as $nvd
  | cna as $cna
  | nvd.analyzed as $analyzed
  | ([$nvd[] | .matched[] |= (.source = "nvd")]
     + [$cna[] | .matched[] |= (.source = "cna") | {id, matched, cna: .cve}])
  | group_by(.id)
  | map(
      (map(select(.cve)) | first) as $from_nvd
      | (map(select(.cna)) | first) as $from_cna
      | {id: .[0].id,
         sources: ([if $from_nvd then "nvd" else empty end, if $from_cna then "cna" else empty end]),
         matched: (map(.matched[])),
         cve: ($from_nvd.cve // $from_cna.cna),
         cna: $from_cna.cna}
      + (if $from_nvd == null and $analyzed != null then
           {nvd_analyzed: ($analyzed | index($from_cna.id) | . != null)}
         else {} end));
