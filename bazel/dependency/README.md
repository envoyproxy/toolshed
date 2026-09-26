# Dependency updaters

This package contains three update tools:

- `updater` for legacy `WORKSPACE` / `versions.bzl` flows
- `registry_updater` for pinned `--registry=` entries in `.bazelrc`
- `module_updater` for `bazel_dep(...)` versions in `MODULE.bazel`

## Registry updater

`registry_updater` rewrites a `.bazelrc` `--registry=<url>/<sha>` pin, but it
also generates read-only runnables for resolving and checking registry SHAs.

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
    branch = "main",
    release_tags = None,
    visibility = None,
    **kwargs
)
```

The macro creates three public entry points:

- `<name>` keeps the existing `write_source_files` behavior and rewrites
  `bazelrc` in place.
- `<name>.resolve` prints the resolved JSON to stdout without writing files.
- `<name>.check` reads the current pin from `bazelrc`, verifies it, and prints a
  JSON status line.

Everything remains Linux-only and `manual`-tagged. The build action behind
`<name>` is marked `local`, `no-cache`, `no-remote`, and `requires-network`,
and it uses the hermetic `//git:toolchain_type` git toolchain plus the jq
toolchain rather than host binaries.

### Build settings

`registry_updater` consumes these public build settings:

- `//dependency:registry_sha`: explicit 40-hex commit to pin. Empty resolves the
  latest target.
- `//dependency:registry_allow_unsafe`: bypass ancestor verification with a
  warning.

From a consumer repository, pass them with the toolshed repo qualifier:

```bash
bazel run @envoy_toolshed//dependency:update_registry   --@envoy_toolshed//dependency:registry_sha=0123456789abcdef0123456789abcdef01234567
```

or to bypass verification explicitly:

```bash
bazel run @envoy_toolshed//dependency:update_registry   --@envoy_toolshed//dependency:registry_sha=0123456789abcdef0123456789abcdef01234567   --@envoy_toolshed//dependency:registry_allow_unsafe=true
```

### Resolve semantics

Resolution always starts from `repo`, `url`, and `branch`; callers never pass
registry URLs on the CLI.

- If `registry_sha` is empty and `release_tags` is `None`, the target is the
  current head of `branch`.
- If `registry_sha` is empty and `release_tags` is set, the target is the
  highest matching tag, ordered with `bazel/version.jq` after stripping a
  leading `v`.
- If `registry_sha` is set, it must be a full 40-character hex SHA.

When the target differs from the current branch head, the resolver performs a
commit-only fetch of `branch` and refuses non-ancestor SHAs with exit code `2`
unless `registry_allow_unsafe=true`.

`<name>.resolve` prints:

```json
{"sha":"<40hex>","url":"<url>/<sha>","branch":"main","latest":"<40hex>","ancestor":true,"tags":["v1.2.3"],"requested":"","unsafe":false}
```

### Check semantics

`<name>.check` reads the current `--registry=<url>/<sha>` pin from `bazelrc`,
fails if that pin is absent or differs across matching lines, and prints:

```json
{"sha":"<40hex>","ancestor":true,"tags":["v1.2.3"],"latest":"<40hex>","behind":1}
```

Exit codes:

- `0`: resolved or checked successfully.
- `2`: refused SHA, missing pin, or non-ancestor pin without `allow_unsafe`.

If `allow_unsafe` is set, `.resolve` and `.check` still print JSON but emit a
`WARNING:` line on stderr when verification is bypassed.

### Output options

Both `.resolve` and `.check` accept:

- `--format=json|markdown`: choose the stdout rendering (default `json`).
  Markdown renders a single status line, eg
  ``pinned to `<sha>`, tags: v1.2.3, behind main by 1``.
- `--markdown-out=<path>`: write the markdown rendering to a file.
- `--sha-out=<path>`: write the raw resolved/checked SHA to a file.
- `--json-out=<path>`: write the JSON to a file. When set and
  `--format=json`, nothing is printed on stdout.

Because `.resolve` and `.check` are `sh_binary` targets with baked `args`,
extra options can be appended after `--` in `bazel run`:

```bash
bazel run //dependency:update_registry.check --   --json-out=/tmp/registry.json   --sha-out=/tmp/registry-sha.txt   --markdown-out=/tmp/registry-status.md
```

### Consumer example

Downstream CI can layer release policy on top of `.check` output without baking
that policy into toolshed. For example, require tags on release branches but
allow untagged dev pins:

```bash
status_json="$(bazel run @envoy_toolshed//dependency:update_registry.check)"
tags="$(printf '%s\n' "${status_json}" | jq -r '.tags | join(",")')"
if [[ -z "${tags}" && "${VERSION}" != *-dev ]]; then
  echo "registry pin must point at a tagged release" >&2
  exit 1
fi
```

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
module. Dependencies with a `local_path_override(...)`, `git_override(...)`, or
`archive_override(...)` are excluded because they are not registry-resolved and
cannot be updated by this tool; `single_version_override(...)` deps are still
included.

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

Report mode also renders markdown, either to stdout or to a file:

```bash
bazel run //dependency:update_module -- --report --format=markdown
bazel run //dependency:update_module -- --report   --json-out=/tmp/report.json   --markdown-out="$GITHUB_STEP_SUMMARY"
```

`--format=json|markdown` (default `json`) selects the stdout rendering, and
unknown formats fail with exit code `1`. When `--json-out` is set and
`--format=json`, nothing is printed on stdout. The markdown rendering is a
single table with non-dev rows first, dev rows marked inline on the name
(`` zlib _(dev)_ ``), and an `Outdated dependencies: N (dev: M)` header.

Each dependency entry includes:

- `current`: version from the input JSON
- `current_registry`: registry hint from the input JSON when present, otherwise
  the first configured registry that serves the current version
- `dev_dependency`: true when the `bazel_dep` is declared with
  `dev_dependency = True`
- `registries`: map of registry URL/path to `{versions, yanked}`
- `latest_by_registry`: highest non-yanked version per serving registry
- `latest`: highest non-yanked version on `current_registry`
- `latest_any`: highest non-yanked version across all serving registries
- `update_available`: true when `latest` is newer than `current`
- `cross_registry_update_available`: true when another registry is ahead of the
  current registry

Use `--fail-on-outdated` to make report mode exit non-zero when any non-dev
dependency has a same-registry update available. Dev dependencies are ignored;
add `--fail-on-outdated-dev` to also fail when a dev dependency is outdated.

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
