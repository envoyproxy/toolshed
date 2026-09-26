# Dependency updaters

This package contains three update tools:

- `updater` for legacy `WORKSPACE` / `versions.bzl` flows
- `registry_updater` for pinned `--registry=` entries in `.bazelrc`
- `module_updater` for `bazel_dep(...)` versions in `MODULE.bazel`

## Registry updater

`registry_updater` rewrites a `.bazelrc` `--registry=<url>/<sha>` pin to the
current commit for a branch in a git-backed Bazel registry.

```starlark
load("@envoy_toolshed//dependency:macros.bzl", "registry_updater")

registry_updater(
    name = "update_registry",
    bazelrc = "//:.bazelrc",
)
```

Signature:

```starlark
registry_updater(
    name,
    bazelrc,
    repo = "https://github.com/envoyproxy/bazel-registry.git",
    url = "https://raw.githubusercontent.com/envoyproxy/bazel-registry",
    ref = "main",
    visibility = None,
    **kwargs
)
```

The updater creates a `write_source_files` runnable plus private helper targets
to resolve the current registry commit and rewrite the selected `.bazelrc`.
Those helper actions are tagged `manual` so `//...` does not trigger the
networked resolution step. The generated helper targets are Linux-only, matching
the currently supported hermetic git toolchain platforms.

The registry resolution action is marked `local`, `no-cache`, `no-remote`, and
`requires-network`, and it uses the hermetic `//git:toolchain_type` git
toolchain rather than host git.

## Module updater

`module_updater` reports and updates `bazel_dep` versions for a single
`MODULE.bazel`, using dependency metadata JSON plus registries discovered from a
`.bazelrc` or an explicit registry list.

```starlark
load("@envoy_toolshed//dependency:macros.bzl", "module_deps_json", "module_updater")

module_deps_json(
    name = "deps_json",
    lockfile = "//:MODULE.bazel.lock",
    module_file = "//:MODULE.bazel",
)

module_updater(
    name = "update_module",
    dependencies = ":deps_json",
    module_file = "//:MODULE.bazel",
    bazelrc = "//:.bazelrc",
)
```

Signature:

```starlark
module_updater(
    name,
    dependencies,
    module_file,
    bazelrc = None,
    registries = None,
    visibility = None,
    **kwargs
)
```

`dependencies` is a JSON map keyed by module name. Each entry needs a `version`,
and may provide a `registry` hint. `module_deps_json` takes both a
`MODULE.bazel.lock` and a `MODULE.bazel`: the dependency set and `version` come
from the `bazel_dep(...)` calls in `module_file` via hermetic `buildozer`, the
registry hint comes from the lockfile, and a `selected` field is emitted when
MVS selected a different version than the one declared in `module_file`. It
fails if the lockfile reports more than one selected version for the same
module.

Consumers that derive dependency JSON from the lockfile alone, such as
envoy's `@envoy_mod_graph//:deps.json`, will over-report transitive modules and
should switch to this macro.

### Report mode

Run report mode with:

```bash
bazel run //dependency:update_module -- --report
```

or write the JSON to a file:

```bash
bazel run //dependency:update_module -- --report --json-out=/tmp/report.json
```

Each dependency entry includes:

- `current`: version from the input JSON
- `current_registry`: registry hint from the input JSON when present, otherwise
  the first configured registry that serves the current version
- `registries`: map of registry URL/path to `{versions, yanked}`
- `latest_by_registry`: highest non-yanked version per serving registry
- `latest`: highest non-yanked version on `current_registry`
- `latest_any`: highest non-yanked version across all serving registries
- `update_available`: true when `latest` is newer than `current`
- `cross_registry_update_available`: true when another registry is ahead of the
  current registry

Use `--fail-on-outdated` to make report mode exit non-zero when any dependency
has a same-registry update available.

### Update mode

Update a dependency with:

```bash
bazel run //dependency:update_module -- bazel_skylib
```

or pin an explicit version:

```bash
bazel run //dependency:update_module -- protobuf=35.2.bcr.envoy
```

By default, updates stay on the dependency's current registry. If another
registry has a newer version, that still appears in the report, but the updater
does not silently jump registries. Use `--registry=<url>` to select another
registry explicitly.

Edits go through hermetic `buildozer` from `buildifier_prebuilt`, so the touched
call is rewritten with buildifier's normal formatting. Matching
`single_version_override(...)` blocks are updated alongside the `bazel_dep(...)`
when they exist.

Yanked versions are rejected unless `--allow-yanked` is passed.

### Notes

- The tool operates on one `MODULE.bazel` at a time.
- Lockfile regeneration stays the caller's responsibility (for example
  `bazel mod deps --lockfile_mode=update` in consumer CI).
- This repository does not currently expose a hermetic curl toolchain, so
  `http(s)` registry fetches require `curl` on `PATH` or `CURL_BIN` to point to
  an explicit curl binary. Local directory and `file://` registries are
  supported for offline tests.
