# jq rules

Load `JqInfo`, `JQ_TOOLCHAIN_TYPE`, `jq_library`, `jq_binary`, and `jq_test`
from `@envoy_toolshed//jq:defs.bzl`. These rules use Aspect's existing jq
toolchain; they do not register or download a separate toolchain.

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

Each library copies its sources (including generated files) into one staged
directory. Import paths are package-relative, with `strip_import_prefix` removed
and `import_prefix` prepended. A strip prefix beginning with `/` is relative to
the repository root instead. Prefixes must be normalized paths without `..`.
The example provides `import "app/str" as str;` and
`import "app/config" as $config;`. In a top-level program (an inline `filter`
or `-f main.jq`), `import "./x"` resolves relative to the working directory.
Inside a module, it resolves relative to the importing module's own file,
preserving the staged layout. Put shared code in a `jq_library` rather than
next to `main.jq`.

`JqInfo.roots` is a preorder depset: the library's own root comes first,
followed by its dependencies in declaration order (shared roots appear once).
Each root becomes a `-L` flag. Collisions inside one library are analysis
errors; across libraries, the first root wins. In a diamond, the first-listed
dependency's roots win over a later sibling shadowing the same import path;
to shadow a transitive module, list the overriding library first in `deps`
(see `diamond_order_test` in `test/BUILD`).
`JqInfo.transitive_srcs` contains the original, unstaged `.jq`/`.json` source
Files across the transitive closure, including generated sources, for aspects
and linters. `DefaultInfo.files` contains the library's own staged root.
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
Bazel runfiles, resolving each root's marker rather than the directory so
manifest-only runfiles work too. Named inputs become `--slurpfile name path`.
Flags in `jq_args` precede the filter; runtime positional inputs follow it.
The standard Bazel `args` attribute retains its usual meaning (pre-seeded argv).
The executable forwards `JqInfo` and works with `bazel run`, shell tests,
genrule `tools`, and rules accepting executable tools.

To generate files, compose with Aspect's `run_binary` or a genrule rather than
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
after the program and any `srcs`.

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

Cases mode's `%%FAIL` diagnostics are matched against jq 1.7's error text
(the pinned toolchain); expectations may need updating if that pin changes.

Run the rules' own tests from the `bazel/` module root:
`bazel test //jq/...`.

Also check manifest-only root resolution manually from that directory:
`bazel test //jq/test:assertion_test //jq/test:cases_test --nobuild_runfile_links --nocache_test_results`.
