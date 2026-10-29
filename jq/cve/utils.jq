import "version" as version;
import "ansi" as ansi;

def to_date_string(datestring):
  datestring
  | sub("\\.[0-9]+"; "")
  | sub("Z$"; "")
  | . + "Z"
  | fromdateiso8601
  | strftime("%Y-%m-%d");

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
             cpes: $cpes}));

def iterate_cves(cves; deps; ignored):
  [cves[]
   | . as $cve
   | select(ignored | index($cve.cve.id) | not)
   | [.cve.configurations[]?.nodes[]?.cpeMatch[]?
      | parse_cve_cpe(.; $cve)]
   | matching_deps(.; deps)
   | select(length > 0)
   | {id: $cve.cve.id, matched: ., cve: $cve.cve}];

# Both arguments have jq --slurpfile shape; dependencies are already parsed.
def scan($deps; $ignored):
  deps_list($deps[0]) as $dependencies
  | iterate_cves(.vulnerabilities; $dependencies; $ignored[0]);

def matched_dependencies(cve):
  cve as $cve
  | cve.matched[]
  | "Dep: \(ansi::green)\(ansi::bold)\(.dep.name)@\(.dep.version.string)\(ansi::reset) \(ansi::green)(\(.dep.release_date)\(ansi::reset))

  Severity: \(get_severity($cve.cve.metrics))
  Published: \(to_date_string($cve.cve.published))
  CPE: \(first(matching_cpe_tags(.cpe.cpe; .dep)).match // "")
  Version: \(.cpe.cpe.version)
  Start (including/excluding): \(.cpe.versions.start_inc // "")/\(.cpe.versions.start_exc // "")
  End (including/excluding): \(.cpe.versions.end_inc // "")/\(.cpe.versions.end_exc // "")

  ---------------------------------

  \($cve.cve.descriptions[0].value)

  ";

def cve_report(cve):
  "================ \(ansi::red)\(ansi::bold)\(ansi::underline)\(cve.id)\(ansi::reset) ================
  \(matched_dependencies(cve))
  ";

def summary(matches):
  "
  ==========================================
  \(ansi::red)\(ansi::bold)\(matches | length) potential CVE vulnerabilities found\(ansi::reset)";

def report(matches):
  matches as $matches
  | (matches | map(cve_report(.)) | join("\n")) + summary($matches);
