include "version";

def parse_declared:
  split("\n")
  | map(select(length > 0) | split(" ") as $fields
      | if ($fields | length) < 2 then
          error("Invalid declared bazel_dep entry: \(.)")
        elif $fields[1] == "(missing)" then
          error("Declared dependency \($fields[0]) is missing version in MODULE.bazel")
        else
          {($fields[0]): $fields[1]}
        end)
  | add // {};

def parse_lockfile:
  .registryFileHashes // {}
  | keys
  | map(select(test("^.+/modules/[^/]+/[^/]+/source\\.json$")))
  | map(capture("^(?<registry>.+)/modules/(?<name>[^/]+)/(?<version>[^/]+)/source\\.json$"))
  | group_by(.name)
  | map((sort_by(.version | version_key)) as $entries
        | if ($entries | length) > 1 then
            error("Multiple source.json entries for module \($entries[0].name): \(($entries | map(.version)) | join(", "))")
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

($declared | parse_declared) as $declared_deps
| (parse_lockfile) as $lockfile_deps
| $declared_deps
| to_entries
| map(. as $dep
    | ($lockfile_deps[$dep.key] // error("Declared dependency \($dep.key) not found in MODULE.bazel.lock; regenerate the lockfile")) as $lockfile_dep
    | (module_url($lockfile_dep.registry; $dep.key; $dep.value)) as $module_url
    | {
        ($dep.key): ({
          module_url: $module_url,
          registry: $lockfile_dep.registry,
          urls: [$module_url],
          version: $dep.value,
        } + if $lockfile_dep.version != $dep.value then
              {selected: $lockfile_dep.version}
            else
              {}
            end),
      })
| add // {}
