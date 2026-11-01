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
| `cve/` | NVD and CVE Program CVE matching and terminal reports (`utils.jq`, `matcher.jq`, `nvd_scan.jq`, `cna_matcher.jq`, `merge.jq`, `report.jq`) |
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

Through Bazel, against `//:jq` (`rules_jq`'s hermetic jq, as consumers get) and
the `aspect_bazel_lib` yq toolchain:

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

### CVE Program records

NVD only adds CPE configurations when it analyzes a CVE, and most recently
published CVEs are unanalyzed (`Awaiting Analysis`, `Received`) or will never
be (`Deferred`), so they can never match above. `utils::scan_cna($deps;
$ignored)` (executable: `cve/cna_matcher.jq`) reads compacted CVE Program
(cvelistV5) records, `{records: [{id, assigner, published, descriptions,
metrics, affected}]}` as written by `dependency/cve:cvelist_fetch`, and
matches the CNA/ADP asserted `affected[]` entries instead:

- on `cpes`, where an entry carries them, against the dependency CPE tags, or
- on `vendor`/`product` (case-insensitively) against the dependency's
  `names`: the CPE tags, the same with any `_project` vendor suffix removed,
  and the github `owner`/`repo` of the first `github.com` url in the
  dependency's `urls`, `project_url` or `license_url`.

Versions come from the `versions[]` entries, as `lessThan` /
`lessThanOrEqual` ranges starting at `version` (a trailing `.*` on a limit
covers the rest of that series, up to the next series' lowest pre-release),
free-text constraints (`< 1.34.7`, `>= 2.0, < 2.1.3`; repeated bounds
intersect) or single versions; `versionType: git` entries (commit
ranges) and constraints that do not parse are ignored. As in the CVE record
format, the first entry covering the dependency version decides its status,
after applying that entry's `changes[]` at or below the version (the last
applicable change wins); `defaultStatus` applies when no entry covers it. The release-date policy applies as for NVD. The records returned
have the shape `{id, matched: [{affected, dep}], cve}`.

`utils::nvd_scan($deps; $ignored)` (executable: `cve/nvd_scan.jq`) returns
`{matches, analyzed}` from one pass over NVD data: the `scan` matches and the
ids of records that have CPE configurations. `utils::merge_sources(nvd; cna)`
(executable: `cve/merge.jq`, with the NVD result as `$nvd`) unions the two
match sets by id: each result carries `sources`, each matched dependency a
`source`, `cve` is the NVD record where there is one (else the CVE Program
record, also kept as `cna`), and CVE Program only matches record
`nvd_analyzed`. Deps are indexed by their candidate names, so the CNA pass
costs little more than parsing the records. `utils::report` labels each
matched dependency with its source, notes NVD's state for CVE Program only
matches, and counts by source in the summary.

## Consuming from Bazel

### `toolshed_jq`

`defs.bzl`'s `toolshed_jq()` runs jq at build time through
[`rules_jq`](../rules_jq): a `jq_binary` over this module's `jq_library`
(`//:library`), run by a genrule that writes `out` (default `<name>.json`). Any
filter can `import`/`include` the scoped modules above. `args` follow the filter
and get genrule expansions such as `$(location)`; `srcs` follow `args`, and with
none jq runs with `--null-input`.

Rules using `rules_jq` directly can depend on `@envoy_toolshed_jq//:library`.

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

### `@envoy_toolshed_jq//:jq`

jq with the modules importable, for scripts and actions that run jq
themselves: use it in place of the toolchain jq, with no `-L`, eg
`"$JQ_BIN" -n 'import "str" as str; "  x  " | str::trim'`. It is a
pass-through `rules_jq` `jq_binary`, so add it to `data` (or `tools`) and pass
its `$(rlocationpath)`/`$(execpath)`.

### `jq_module_test`

`defs.bzl`'s `jq_module_test()` wraps one `tests/<scope>/<module>/`
directory's `.test.yml` cases as an `sh_test`, running `run-tests.sh` with
`JQ_BIN` pointed at `//:jq` and `YQ_BIN` at the aspect yq toolchain:

```starlark
load("@envoy_toolshed_jq//:defs.bzl", "jq_module_test")

jq_module_test(
    name = "test_github_gfm",
    module = "github/gfm",
)
```

See `jq/BUILD` for the full set of `jq_module_test` targets exercised by
`bazel test //...` in this directory.
