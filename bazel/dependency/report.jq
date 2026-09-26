include "version";

def sorted_versions($values): ($values // []) | sort_versions;
def non_yanked($versions; $yanked): $versions | map(. as $v | select(($yanked | index($v)) == null));
def latest_non_yanked($versions; $yanked): non_yanked($versions; $yanked) | latest_version;
def first_registry_for($registries; $current): $registries | map(select((.value.versions | index($current)) != null)) | .[0].key?;
def cmp_gt($a; $b): $a != null and ($b == null or compare_versions($a; $b) == 1);
def nonempty_string_or_null($value): if ($value | type) == "string" and ($value | length) > 0 then $value else null end;

{deps: $deps, registries: $registries, metadata: $metadata} as $input
| $input.deps
| to_entries
| map(select(.value.version | type == "string"))
| map(. as $dep |
    ($input.registries
     | map(. as $registry | {key: $registry, value: ($input.metadata[$registry][$dep.key] // null)})
     | map(select(.value != null))
     | map({key, value: {versions: sorted_versions(.value.versions), yanked: sorted_versions((.value.yanked_versions // {}) | keys)}})) as $registries
    | ((nonempty_string_or_null($dep.value.registry) // first_registry_for($registries; $dep.value.version) // null)) as $current_registry
    | ($registries | map({key, value: latest_non_yanked(.value.versions; .value.yanked)}) | map(select(.value != null)) | from_entries) as $latest_by_registry
    | (if $current_registry == null then null else ($latest_by_registry[$current_registry] // null) end) as $latest
    | ($latest_by_registry | to_entries | map(.value) | latest_version) as $latest_any
    | {($dep.key): {
        current: $dep.value.version,
        current_registry: ($current_registry // null),
        selected: ($dep.value.selected // null),
        registries: ($registries | from_entries),
        latest_by_registry: $latest_by_registry,
        latest: ($latest // null),
        latest_any: ($latest_any // null),
        update_available: (cmp_gt($latest; $dep.value.version)),
        cross_registry_update_available: (cmp_gt($latest_any; $latest))
      }}
  )
| add // {}
