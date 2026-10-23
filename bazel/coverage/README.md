# Coverage reports

Reusable Bazel 9 / bzlmod coverage reporting using grcov, jq, and zstd.
Consumers retain their thresholds, directory exceptions, and `.bazelrc` configs.

## Setup

Enable grcov in the consumer's `MODULE.bazel`:

```starlark
grcov = use_extension("@envoy_toolshed//coverage/grcov:extensions.bzl", "grcov_extension")
grcov.setup()
use_repo(grcov, "grcov")
```

Define a report in a BUILD file:

```starlark
load("@envoy_toolshed//coverage:macros.bzl", "coverage_report")

label_flag(
    name = "config",
    build_setting_default = "//test:coverage_config",
)

coverage_report(
    name = "report",
    config = ":config",
    # templates = [":base.html", ":index.html", ":macros.html"],
    source_root = "source",
    source_glob = "*.cc",
    # grcov = "@grcov//:grcov",
    # zstd = "@zstd//:zstd_cli",
    visibility = ["//visibility:public"],
)
```

Signature:
`coverage_report(name, config, templates=None, source_root="source", source_glob="*.cc", zstd=..., grcov=..., visibility=None)`.
Template overrides are three labels in **base, index, macros** order.
The default compressor is toolshed's BCR zstd dependency, not a host binary;
grcov can be supplied from a consumer-owned repository.
Generated targets are `:report_grcov_config`, `:report`, and `:report.validate`.

The config label must produce one JSON file (including through a `label_flag`):

```json
{
  "thresholds": {"total": 90, "per_directory": 95},
  "directories": {"source/extensions/example": 80}
}
```

The equivalent YAML may be converted to JSON by the consumer's yq rule:

```yaml
thresholds:
  total: 90
  per_directory: 95
directories:
  source/extensions/example: 80
```

Thresholds are percentages; missing thresholds default to zero.
`directories` maps workspace-relative paths to exception thresholds. When it
is present, the generator discovers directories containing `source_glob` files
under `source_root`. Directories absent from grcov output are skipped.
A null config disables directory validation.

Wire the report into the consumer's `.bazelrc`:

```text
coverage:test-coverage --coverage_report_generator=//tools/coverage:report
```

Different root modules, such as mobile, may select their own config using the
same `label_flag` pattern or `--//tools/coverage:config=//test:mobile_coverage_config`.
No workspace-name or cwd sniffing is performed.

## Local source-tree requirement

Report generation is inherently local: grcov needs access to the real source
tree. Configure the consumer's coverage report action for local execution.
The generator accepts `--workspace=/absolute/root`, otherwise uses
`BUILD_WORKSPACE_DIRECTORY` for `bazel run`. During a coverage action, it resolves
the execroot's source symlinks back to the real workspace, including symlink
farms with ordinary parent directories. If this cannot be resolved, it fails
with instructions to supply `--workspace`.
Tool, config, jq module, and template paths are resolved through Bazel runfiles.
The report is a zstd-compressed tar archive containing HTML, covdir, and
`coverage.json`; it is written to Bazel's requested `--output_file`.

## Driver

Run the exported `@envoy_toolshed//coverage:run.sh` directly, or:

```sh
bazel run @envoy_toolshed//coverage:run -- \
  --config=test-coverage \
  --validate-target=//tools/coverage:report.validate \
  //test/...
```

The driver runs Bazel from `BUILD_WORKSPACE_DIRECTORY`, then `SRCDIR`, then cwd.
It runs coverage, checks the archive is nonempty, renames it to `.tar.zst`,
decompresses via `bazel run` of the zstd target, and extracts into the output
directory. Existing output files are overwritten, not recursively deleted.
Validation is enabled by default and requires `--validate-target` or
`COVERAGE_VALIDATE_TARGET`; `--no-validate` disables it.

Options:

| Flag | Default / environment fallback |
| --- | --- |
| `--fuzz` | `FUZZ_COVERAGE=true`; filters targets using a Bazel tags query |
| `--summary-only` | Off; ignores per-directory failures during validation |
| `--no-validate` | `VALIDATE_COVERAGE=false` |
| `--config=NAME` (repeatable) | Coverage configs; none implicitly added |
| `--validate-config=NAME` (repeatable) | Validation configs; none implicitly added |
| `--output-dir=DIR` | Workspace-relative `generated/coverage`, or `generated/fuzz_coverage` |
| `--validate-target=LABEL` | `COVERAGE_VALIDATE_TARGET`; otherwise required |
| `--bazel-opt=OPT` (repeatable) | Appended to whitespace-split `BAZEL_BUILD_OPTION_LIST` |
| `--query-opt=OPT` (repeatable) | Appended to whitespace-split `BAZEL_QUERY_OPTION_LIST` |
| `--grpc-log=PATH` | `BAZEL_GRPC_LOG` |
| `--fuzz-tag=PATTERN` | `fuzz_target`; a Bazel query regex |
| `[--] TARGET...` | Whitespace-split `COVERAGE_TARGET`, otherwise `//test/...` |

`COVERAGE_ZSTD_TARGET` overrides the decompressor label. The Bazel binary
provides a canonical default label; direct script callers must expose
`@zstd//:zstd_cli` or set that variable.
All runs include `--heap_dump_on_oom` and
`--experimental_ui_max_stdouterr_bytes=80000000`.

## Validation

```sh
bazel run //tools/coverage:report.validate -- /absolute/path/coverage.json
bazel run //tools/coverage:report.validate -- /absolute/path/coverage.json --summary-only
```

Default mode prints `summary_report` when failed or adjustable directories
exist, otherwise `summary_message`. It fails for any failed directory or an
unreached overall threshold. Summary-only mode prints `summary_message` and
fails only when `summary.threshold_reached` is false.

## Envoy follow-up

* Delete `tools/coverage/{filter.jq,report_generator.sh.template,validate.sh,templates/}`
  and `test/run_envoy_bazel_coverage.sh`.
* Keep config conversion, thresholds, directory exceptions, and coverage configs
  in Envoy. Replace `tools/coverage/BUILD` machinery with `label_flag(config)`
  and `coverage_report(name="report", config=":config")`.
* Set `.bazelrc`'s `--coverage_report_generator=@envoy//tools/coverage:report`.
* Have `ci/do_ci.sh` invoke `@envoy_toolshed//coverage:run.sh` with
  `--config=test-coverage`, or
  `--fuzz --config=fuzz-coverage --validate-config=fuzz-coverage-config`,
  and `--validate-target=@envoy//tools/coverage:report.validate`.
* Mobile passes `--summary-only` and selects its own coverage config.
