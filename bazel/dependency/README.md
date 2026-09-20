# `//dependency`

## `registry_snapshot`

Declare the registry snapshot repository in `MODULE.bazel`:

```starlark
registry = use_extension("@envoy_toolshed//dependency:registry.bzl", "registry_ext")
registry.snapshot(
    name = "registry_snapshot",
    repo = "https://github.com/envoyproxy/bazel-registry",
    branch = "main",
    url_prefix = "https://github.com/envoyproxy/bazel-registry/archive/",
)
use_repo(registry, "registry_snapshot")
```

- `--repo_env=REGISTRY_HASH=<sha>` pins the fetched snapshot.
- `--repo_env=REGISTRY_SKIP_CHECK=1` skips the ancestry/tag validation probe and records `skip_check: true` in `info.json`.

The generated repo exports:

- `@registry_snapshot//:info`
- `@registry_snapshot//:index`

## `registry_updater`

`registry_updater` builds a graph of `jq()` targets for registry planning/checking and a runnable source-writer target.

```starlark
load("@envoy_toolshed//dependency:macros.bzl", "registry_updater")

registry_updater(
    name = "registry",
    bazelrc_files = ["//:.bazelrc", "//api:.bazelrc"],
    module_files = ["//:MODULE.bazel", "//api:MODULE.bazel"],
    version_file = "//:VERSION.txt",
)
```

The updater expects a snapshot repo named `@<name>_snapshot` (for `name = "registry"`, `@registry_snapshot`).

### Flags

- `--//pkg:registry.set=foo=1.2.3`
- `--//pkg:registry.check_only`
- `--repo_env=REGISTRY_HASH=<sha>`
- `--repo_env=REGISTRY_SKIP_CHECK=1`

### Useful targets

- `bazel run //pkg:registry` writes the updated source files, then prints check messages and the rendered report.
- `bazel build //pkg:registry.check_ok` validates the snapshot/check/plan without writing.
- `bazel build //pkg:registry.report_text` builds the human-readable report text.
- `bazel build //pkg:registry.report` builds the JSON report.
- `bazel build //pkg:registry.edits` builds the JSON file-edit list.

The JSON report is a declared output (`bazel-bin/.../registry.report.json`), so consumers can copy it directly from `bazel-bin`.
