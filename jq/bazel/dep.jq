import "bazel/version" as version;

def parse_declared:
  split("\n")
  | map(select(length > 0) | split(" ") as $fields
      | if ($fields | length) < 2 then
          error("Invalid declared bazel_dep entry: \(.)")
        elif $fields[1] == "(missing)" then
          error("Declared dependency \($fields[0]) is missing version in MODULE.bazel")
        else
          {($fields[0]): {version: $fields[1], dev: (($fields[2] // "False") == "True")}}
        end)
  | add // {};

def parse_overridden:
  split("\n")
  | map(select(length > 0)
      | if . == "(missing)" then
          error("Override is missing module_name in MODULE.bazel")
        else
          .
        end);

def parse_lockfile:
  .registryFileHashes // {}
  | keys
  | map(select(test("^.+/modules/[^/]+/[^/]+/source\\.json$")))
  | map(capture("^(?<registry>.+)/modules/(?<name>[^/]+)/(?<version>[^/]+)/source\\.json$"))
  | group_by(.name)
  | map((sort_by(.version | version::version_key)) as $entries
        | if ($entries | length) > 1 then
            (($entries | map(.version)) | join(", ")) as $versions
            | error("Multiple source.json entries for module \($entries[0].name): \($versions)")
          else
            {
              ($entries[0].name): {
                registry: ($entries[0].registry + "/"),
                version: $entries[0].version,
              },
            }
          end)
  | add // {};

def module_url($registry; $name; $version):
  $registry + "modules/" + $name + "/" + $version + "/";

def deps_json($declared; $overridden):
  ($declared | parse_declared) as $declared_deps
  | ($overridden | parse_overridden) as $overridden_deps
  | (parse_lockfile) as $lockfile_deps
  | $declared_deps
  | to_entries
  | map(. as $dep
      | if ($overridden_deps | index($dep.key)) != null then
          empty
        else
          ($lockfile_deps[$dep.key] // error("Declared dependency \($dep.key) not found in MODULE.bazel.lock; regenerate the lockfile")) as $lockfile_dep
          | (module_url($lockfile_dep.registry; $dep.key; $dep.value.version)) as $resolved_module_url
          | {
              ($dep.key): ({
                dev_dependency: $dep.value.dev,
                module_url: $resolved_module_url,
                registry: $lockfile_dep.registry,
                urls: [$resolved_module_url],
                version: $dep.value.version,
              } + if $lockfile_dep.version != $dep.value.version then
                    {selected: $lockfile_dep.version}
                  else
                    {}
                  end),
            }
        end)
  | add // {};

def normalize_registry:
  sub("/+$"; "") + "/";

def dedupe_preserve:
  reduce .[] as $item ([]; if index($item) == null then . + [$item] else . end);

def registries($extra):
  ($extra // [])
  + (split("\n")
     | map(sub("\\s+#.*$"; ""))
     | map(select(test("^\\s*#") | not))
     | map(try capture("^\\s*(?:common|build)(?::[^\\s]+)?\\s+--registry=(?<registry>\\S+)").registry catch empty)
     | map(select(type == "string" and length > 0))
     | map(normalize_registry))
  | dedupe_preserve;

def metadata_versions($regs; $deps):
  def base:
    reduce $regs[] as $registry ({}; .[$registry] = (reduce $deps[] as $dep ({}; .[$dep] = null)));

  reduce [inputs | {path: input_filename, value: .}][] as $input
    (base;
     ($input.path | capture("/(?<i>[0-9]+)/(?<dep>[^/]+)\\.json$")) as $path
     | .[$regs[$path.i | tonumber]][$path.dep] = $input.value);

def sorted_versions($values): ($values // []) | version::sort_versions;
def non_yanked($versions; $yanked): $versions | map(. as $v | select(($yanked | index($v)) == null));
def latest_non_yanked($versions; $yanked): non_yanked($versions; $yanked) | version::latest_version;
def first_registry_for($registries; $current): $registries | map(select((.value.versions | index($current)) != null)) | .[0].key?;
def cmp_gt($a; $b): $a != null and ($b == null or version::compare_versions($a; $b) == 1);
def nonempty_string_or_null($value): if ($value | type) == "string" and ($value | length) > 0 then $value else null end;

def report($deps; $registries; $metadata):
  {deps: $deps, registries: $registries, metadata: $metadata} as $input
  | $input.deps
  | to_entries
  | map(select(.value.version | type == "string"))
  | map(. as $dep |
      ($input.registries
       | map(. as $registry | {key: $registry, value: ($input.metadata[$registry][$dep.key] // null)})
       | map(select(.value != null))
       | map({key, value: {versions: sorted_versions(.value.versions), yanked: sorted_versions((.value.yanked_versions // {}) | keys)}})) as $report_registries
      | ((nonempty_string_or_null($dep.value.registry) // first_registry_for($report_registries; $dep.value.version) // null)) as $current_registry
      | ($report_registries | map({key, value: latest_non_yanked(.value.versions; .value.yanked)}) | map(select(.value != null)) | from_entries) as $latest_by_registry
      | (if $current_registry == null then null else ($latest_by_registry[$current_registry] // null) end) as $latest
      | ($latest_by_registry | to_entries | map(.value) | version::latest_version) as $latest_any
      | {($dep.key): {
          current: $dep.value.version,
          current_registry: ($current_registry // null),
          dev_dependency: ($dep.value.dev_dependency // false),
          selected: ($dep.value.selected // null),
          registries: ($report_registries | from_entries),
          latest_by_registry: $latest_by_registry,
          latest: ($latest // null),
          latest_any: ($latest_any // null),
          update_available: (cmp_gt($latest; $dep.value.version)),
          cross_registry_update_available: (cmp_gt($latest_any; $latest))
        }}
    )
  | add // {};

def report_markdown:
  to_entries
  | sort_by([.value.dev_dependency // false, .key]) as $deps
  | ($deps | map(select(.value.update_available == true and ((.value.dev_dependency // false) | not))) | length) as $outdated
  | ($deps | map(select(.value.update_available == true and (.value.dev_dependency // false))) | length) as $outdated_dev
  | [
      "Outdated dependencies: \($outdated) (dev: \($outdated_dev))",
      "",
      "| Dependency | Current | Latest | Registry | Update? |",
      "| --- | --- | --- | --- | --- |",
      ($deps[]
       | .value as $v
       | "| \(.key)\(if $v.dev_dependency then " _(dev)_" else "" end) | \($v.current // "—") | \($v.latest // "—") | \($v.current_registry // "—") | \(if $v.update_available == true then "✅" else "—" end) |")
    ]
  | join("\n");

def error_result($message): {error: $message};

def resolve($dep; $requested_version; $requested_registry; $allow_yanked; $report_json):
  def nonempty_or_null($value):
    if ($value | type) == "string" and ($value | length) > 0 then $value else null end;

  ($report_json[$dep] // null) as $entry
  | if $entry == null then
      error_result("Dependency \($dep) not found in report")
    else
      ($entry.registries | keys) as $available
      | (nonempty_or_null($requested_registry)) as $selected_registry
      | (nonempty_or_null($requested_version)) as $selected_version
      | (
          if $selected_registry != null then
            $selected_registry
          elif $selected_version != null then
            ($available | map(select((($entry.registries[.].versions // []) | index($selected_version)) != null))) as $matches
            | if ($entry.current_registry != null and ($matches | index($entry.current_registry)) != null) then
                $entry.current_registry
              elif ($matches | length) == 1 then
                $matches[0]
              elif ($matches | length) == 0 then
                error_result("Version \($selected_version) for \($dep) is not published on any configured registry")
              else
                error_result("Version \($selected_version) is available in multiple registries; pass --registry")
              end
          elif $entry.current_registry != null then
            $entry.current_registry
          elif ($available | length) == 1 then
            $available[0]
          else
            error_result("Unable to determine registry for \($dep); pass --registry")
          end
        ) as $registry
      | if ($registry | type) == "object" then
          $registry
        else
          (($selected_version // ($entry.latest_by_registry[$registry] // ""))) as $target
          | if $target == "" then
              error_result("No non-yanked version found for \($dep) on \($registry)")
            elif ((($entry.registries[$registry].versions // []) | index($target)) == null) then
              error_result("Version \($target) for \($dep) is not published on \($registry)")
            elif (($allow_yanked | not) and ((($entry.registries[$registry].yanked // []) | index($target)) != null)) then
              error_result("Version \($target) for \($dep) is yanked on \($registry); pass --allow-yanked to override")
            else
              {target: $target, registry: $registry, current: $entry.current}
            end
        end
    end;

def registries_from_args: registries($ARGS.named.extra);
def metadata_versions_from_args: metadata_versions($ARGS.named.regs; $ARGS.named.deps);
def report_from_args: report($ARGS.named.deps; $ARGS.named.registries; $ARGS.named.metadata);
def resolve_from_args: resolve($ARGS.named.dep; $ARGS.named.requested_version; $ARGS.named.requested_registry; $ARGS.named.allow_yanked; $ARGS.named.report);
