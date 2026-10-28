# `jq/`

Reusable [`jq`](https://jqlang.org/) filter modules, shared by toolshed's own
GitHub Actions/scripts, by `bazel/` in this repo, and by any downstream repo
that wants them.

This directory is its own Bazel module, `envoy_toolshed_jq` (see
`MODULE.bazel`), consumed from `bazel/` via `local_path_override` in
`bazel/MODULE.bazel`. It has no version of its own: it is versioned and
released together with the `envoy_toolshed` module, so `MODULE.bazel`'s
`version` here always matches `bazel/VERSION.txt` and the `envoy_toolshed_jq`
`bazel_dep` pin in `bazel/MODULE.bazel`. It is published alongside
`envoy_toolshed` as `toolshed-jq-v<version>.tar.gz` on the same
`bazel-v<version>` GitHub release.

Modules keep working outside Bazel too: `./jq/run-tests.sh` runs the full
test suite against whatever `jq`/`yq` are on `PATH`, and this is what
`.github/workflows/jq.yml`'s plain (non-Bazel) job uses.

## Scope directories

Modules are grouped by *what shape of data the filter knows about*, not by
which consumer happens to call it. The directory name is the scope:

| Directory | Scope |
|---|---|
| `github/` | GitHub API / Actions / GFM-shaped input or output (`actions.jq`, `gfm.jq`) |
| `bazel/` | Bazel `aquery`/BEP/`BUILD`-shaped data (`aquery.jq`, `dep.jq`, `registry.jq`, `version.jq`) |
| `clang/` | clang tooling output (`tidy.jq`, clang-tidy stdout parsing) |
| `cve/` | NVD CVE matching and terminal reports (`utils.jq`, `matcher.jq`, `report.jq`) |
| `envoy/` | reserved for Envoy release/archive policy filters (not added yet) |
| root | generic helpers with no domain-specific knowledge (`args.jq`, `bash.jq`, `str.jq`, `utils.jq`, `validate.jq`) |

Root `version.jq` parses semantic or opaque dependency versions and compares
parsed objects. It is intentionally separate from `bazel/version.jq`, whose
string-based ordering follows Bazel registry conventions. `ansi.jq` provides
terminal color and style escapes.

`import`/`include` paths mirror this layout, and the import alias is always
the last path segment (the module's basename). A module must not share its
basename with its scope directory, because jq rejects import paths such as
`foo/foo`. For example:

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

## CVE scanner

Prepare a dependency-name dictionary (values containing `cpe`, `version`, and
`release_date`) with `utils::parse_deps(.)`, then pass that JSON and a JSON
array of ignored CVE IDs as slurpfiles.

`cpe` accepts either a single CPE string or a list of CPE strings, for example
`["cpe:2.3:a:c-ares_project:c-ares:*", "cpe:2.3:a:c-ares:c-ares:*"]`.
A CVE can match any tag in the list. Null and `"N/A"` entries are ignored;
dependencies with no remaining tags are skipped. Parsed dependencies contain a
`cpes` array and a backwards-compatible `cpe` alias for its first entry. Reports
show the dependency tag that matched.

For example:

```sh
jq -L jq 'import "cve/utils" as utils; utils::parse_deps(.)' deps.json > parsed-deps.json
jq -L jq --slurpfile deps parsed-deps.json --slurpfile ignored ignored.json \
  -f jq/cve/matcher.jq nvd.json > matches.json
jq -r -L jq -f jq/cve/report.jq matches.json
```

`utils::scan($deps; $ignored)` accepts those same slurpfile arrays and reads an
NVD `{vulnerabilities: [...]}` object from its input. It returns an array of
`{id, matched: [{cpe, dep}], cve}` records. `utils::report($matches)` is the
importable rendering function; `cve/matcher.jq` and `cve/report.jq` are executable
filters, not importable modules. Matching preserves the upstream vendor/product,
version-bound, and release-date policy; it is not an evaluator of NVD's full
configuration boolean expressions.

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
        import "github/actions" as github;
        github::log_bubble({title: "hi", message: "hello"})
    """,
)
```

Consumers outside this repo pull it in as any other `bazel_dep`, pinned to
whatever `envoy_toolshed`'s current release version is (see
`bazel/VERSION.txt`):

```starlark
bazel_dep(name = "envoy_toolshed_jq", version = "<envoy_toolshed version>")
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
