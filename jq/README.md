# `jq/`

Reusable [`jq`](https://jqlang.org/) filter modules, shared by toolshed's own
GitHub Actions/scripts, by `bazel/` in this repo, and by any downstream repo
that wants them.

This directory is its own Bazel module, `envoy_toolshed_jq` (see
`MODULE.bazel`), independent of the `envoy_toolshed` module rooted at
`bazel/`. It is consumed from `bazel/` via `local_path_override` in
`bazel/MODULE.bazel`. It is *not* published as part of the `envoy_toolshed`
release tarball; that's a follow-up.

Modules keep working outside Bazel too: `./jq/run-tests.sh` runs the full
test suite against whatever `jq`/`yq` are on `PATH`, and this is what
`.github/workflows/jq.yml`'s plain (non-Bazel) job uses.

## Scope directories

Modules are grouped by *what shape of data the filter knows about*, not by
which consumer happens to call it. The directory name is the scope:

| Directory | Scope |
|---|---|
| `github/` | GitHub API / Actions / GFM-shaped input or output (`github.jq`, `gfm.jq`) |
| `bazel/` | Bazel `aquery`/BEP/`BUILD`-shaped data (`aquery.jq`) |
| `clang/` | clang tooling output (`tidy.jq`, clang-tidy stdout parsing) |
| `envoy/` | reserved for Envoy release/archive policy filters (not added yet) |
| root | generic helpers with no domain-specific knowledge (`args.jq`, `bash.jq`, `str.jq`, `utils.jq`, `validate.jq`) |

`import`/`include` paths mirror this layout, and the import alias is always
the last path segment (the module's basename), eg:

```jq
import "github/gfm" as gfm;
import "bazel/aquery" as aquery;
import "str" as str;

gfm::collapse(aquery::frag_path($x)) | str::trim
```

`.test.yml` fixtures live under `tests/<scope>/<module>/`, mirroring the
module's own path, eg `tests/github/gfm/*.test.yml` for `github/gfm.jq`.

## Running tests

Bare, against system `jq`/`yq`:

```console
$ ./jq/run-tests.sh              # all tests
$ ./jq/run-tests.sh tests/github/gfm   # just one module's tests
```

Through Bazel, against the hermetic `aspect_bazel_lib` jq/yq toolchains:

```console
$ cd jq && bazel test //...
```

Both entry points run the exact same `run-tests.sh` and `.test.yml` files.

## Consuming from Bazel

### `toolshed_jq`

`defs.bzl`'s `toolshed_jq()` wraps `@aspect_bazel_lib//lib:jq.bzl`'s `jq()`,
adding the `-L <modules root>` flag (and the modules themselves as `data`)
automatically, so any filter can `import`/`include` the scoped modules above:

```starlark
load("@envoy_toolshed_jq//:defs.bzl", "toolshed_jq")

toolshed_jq(
    name = "notice",
    srcs = ["event.json"],
    filter = """
        import "github/github" as github;
        github::log_bubble({title: "hi", message: "hello"})
    """,
)
```

Consumers outside this repo pull it in as any other `bazel_dep`:

```starlark
bazel_dep(name = "envoy_toolshed_jq", version = "0.1.0-dev")
```

(`bazel/MODULE.bazel` instead uses `local_path_override(module_name =
"envoy_toolshed_jq", path = "../jq")`, since `jq/` lives in the same repo.)

### `jq_module_test`

`defs.bzl`'s `jq_module_test()` wraps one `tests/<scope>/<module>/`
directory's `.test.yml` cases as an `sh_test`, running `run-tests.sh` with
`JQ_BIN`/`YQ_BIN` pointed at the aspect toolchains:

```starlark
load("@envoy_toolshed_jq//:defs.bzl", "jq_module_test")

jq_module_test(
    name = "test_github_gfm",
    module = "github/gfm",
)
```

See `jq/BUILD` for the full set of `jq_module_test` targets exercised by
`bazel test //...` in this directory.
