# `rules_jq`

Bazel rules for composable [jq](https://jqlang.org/) libraries, executables and tests.

This directory is its own Bazel module, `rules_jq`, incubating in toolshed. It is not yet
published; toolshed tests it from `bazel/` through a `local_path_override`.

```starlark
bazel_dep(name = "rules_jq", version = "...")
```

Load `JqInfo`, `JQ_TOOLCHAIN_TYPE`, `jq_library`, `jq_binary`, and `jq_test`
from `@rules_jq//jq:defs.bzl`. These rules use the jq toolchain from
[`jq.bzl`](https://github.com/bazel-contrib/jq.bzl), which registers it; they do not register or
download one themselves.

## Libraries

```starlark
jq_library(
    name = "strings",
    srcs = ["modules/str.jq", "modules/config.json"],
    strip_import_prefix = "modules",
    import_prefix = "app",
    deps = [":other_modules"],
)
```

Each library stages its sources (including generated files) as symlinks under one
`<name>.modules/` directory. Import paths are package-relative, with `strip_import_prefix` removed
and `import_prefix` prepended. A strip prefix beginning with `/` is relative to
the repository root instead; for sources from an external repository this is
that repository's root, not the main repository's. Prefixes must be normalized
paths without `..`. The example provides `import "app/str" as str;` and
`import "app/config" as $config;`.

Relative import paths such as `import "./x"` are always resolved against the
`-L` roots, not against the importing file. To import a sibling from inside a
nested module, add a `{search: "./"}` metadata entry, e.g.
`import "./helper" as helper {search: "./"};`; relative `search` values are
resolved relative to the importing module's file (or the working directory for
a top-level `filter` or `-f main.jq`). `test/modules/feature.jq` is a worked
example. Put shared code in a `jq_library` rather than next to `main.jq`.

`JqInfo.roots` is a preorder depset: the library's own root comes first,
followed by its dependencies in declaration order (shared roots appear once).
Each root becomes a `-L` flag. Collisions inside one library are analysis
errors; across libraries, the first root wins. In a diamond, the first-listed
dependency's roots win over a later sibling shadowing the same import path;
to shadow a transitive module, list the overriding library first in `deps`
(see `diamond_order_test` in `test/BUILD`).
`JqInfo.transitive_srcs` contains the original, unstaged `.jq`/`.json` source
Files across the transitive closure, including generated sources, for aspects
and linters. `DefaultInfo.files` contains the library's own staged files, and its
runfiles the transitive staged closure.
Each staged root reserves `.jq_root` as a marker; import paths cannot use that
name as their first component.

## Executables

```starlark
jq_binary(
    name = "notice",
    main = "notice.jq",  # Exactly one of main or filter.
    deps = [":strings"],
    jq_args = ["-r"],
    named_srcs = {"config": ":config.json"},
    data = [],
)
```

The executable resolves jq, module roots, the main file, and named inputs through
Bazel runfiles, resolving each root through its `.jq_root` marker file, so
manifest-only runfiles work too. Named inputs become `--slurpfile name path`.
Flags in `jq_args` precede the filter; runtime positional inputs follow it.
The standard Bazel `args` attribute retains its usual meaning (pre-seeded argv).
The executable forwards `JqInfo` and works with `bazel run`, shell tests,
genrule `tools`, and rules accepting executable tools.

To generate files, compose with `run_binary` (`bazel_lib`) or a genrule rather than
another jq rule. For stdout capture, use a genrule (see `test/BUILD`):

```starlark
genrule(
    name = "notice_output",
    tools = [":notice"],
    outs = ["notice.json"],
    cmd = "$(execpath :notice) > $@",
)
```

## Tests

`jq_test` is a direct Bazel test rule, defaults to `size = "small"`, and forwards
common test attributes such as `args`, `env`, `tags`, `timeout`, and `visibility`.
Use `jq_args` for jq flags; standard `args` and `--test_arg` reach the invocation
after the program and any `srcs`. In cases mode they are not forwarded, since jq
would treat them as extra case files.

* **Assertion:** specify `filter` or `main`. Runs with `-e`, so a final `false`,
  `null`, no output, or jq error fails. `srcs` become positional inputs; without
  `srcs` or declared `args`, `-n` is added. Named inputs can compare documents:
  `named_srcs = {"a": ":a.json", "b": ":b.json"}`,
  `filter = "$a[0] == $b[0]"`.
* **Golden:** additionally set `expected`. Both actual and expected output are
  normalized through `jq -S .` and compared with a readable diff. With
  `raw = True`, output is compared byte-for-byte instead. This mode does not
  add `-e`, so valid `false` and `null` outputs can be golden values.
* **Cases:** specify only `cases` and optional `deps`/test attributes. This runs
  jq's native `--run-tests` backend, without a YAML parser.

For example, standard positional `args` can coexist with jq flags:

```starlark
jq_test(
    name = "input_test",
    filter = '.name == "world"',
    jq_args = ["-c"],
    args = ["$(rootpath input.json)"],
    data = ["input.json"],
)
```

A native case file has a filter line, an input JSON line, one or more expected
JSON lines, and a blank separator. `%%FAIL` introduces a compile-error case:
the next line is the invalid filter and the following line is the expected
diagnostic substring. For example:

```text
import "str" as str; str::trim
" hello "
"hello"

%%FAIL
undefined_function
jq: error: undefined_function/0 is not defined

```

Cases mode's `%%FAIL` diagnostics are matched against the resolved toolchain's error
text (jq 1.7 in toolshed); jq 1.8 adds a column and a source snippet, so
expectations need updating with the jq version.

Run the rules' own tests from the `bazel/` module root:
`bazel test @rules_jq//...`.

Also check manifest-only root resolution manually from that directory:

```console
bazel test @rules_jq//jq/test:assertion_test @rules_jq//jq/test:cases_test \
    --nobuild_runfile_links --nocache_test_results
```
