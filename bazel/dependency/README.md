# `//dependency`

## `registry_updater`

`registry_updater` generates a `sh_binary` that updates pinned
`envoyproxy/bazel-registry` commits in one or more `.bazelrc` files and
reconciles any hosted `MODULE.bazel` pins that the target registry commit no
longer serves.

```starlark
load("@envoy_toolshed//dependency:macros.bzl", "registry_updater")

registry_updater(
    name = "registry",
    bazelrc_files = ["//:.bazelrc", "//api:.bazelrc"],
    module_files = ["//:MODULE.bazel", "//api:MODULE.bazel"],
    version_file = "//:VERSION.txt",
)
```

The generated binary reads and writes the configured source-tree files via
`BUILD_WORKSPACE_DIRECTORY`, with jq module logic loaded from
`@envoy_toolshed_jq//:modules`.

### CLI

```console
$ bazel run //path:registry -- \
    [--hash SHA] [--repo URL] [--branch NAME] [--skip-check] [--check-only] \
    [--set name=version]... [--output PATH] [--dry-run]
```

- `--hash` uses an explicit registry commit; otherwise the tool resolves the
  head of `--branch` from `--repo`.
- `--check-only` validates the currently pinned registry hash without changing
  files.
- `--skip-check` skips registry ancestry/tag checks and is invalid with
  `--check-only`.
- `--set name=version` forces a hosted, already-pinned module to a specific
  registry-served version.
- `--dry-run` prints and writes the planned report without modifying files.

### Report JSON

The tool always writes a JSON report for successful update/dry-run executions
to `--output` (default:
`${REGISTRY_CHANGES_OUTPUT:-${ENVOY_BUILD_DIR:-/build}/registry-changes.json}`):

```json
{
  "registry": {
    "old": "<old commit>",
    "new": "<new commit>"
  },
  "modules": [
    {
      "name": "foo",
      "from": "1.0.0",
      "to": "1.1.0",
      "files": ["MODULE.bazel", "api/MODULE.bazel"]
    }
  ]
}
```
