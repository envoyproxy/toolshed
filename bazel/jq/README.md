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
`import "app/config" as $config;`. Relative imports retain their staged layout;
use jq's search metadata for siblings of a nested module, for example
`import "./helper" as helper {search: "./"};` (jq treats `"."` as the working
directory, not the importing module's directory).

`JqInfo.roots` is a preorder depset: the library's own root comes first,
followed by its dependencies in declaration order (shared roots appear once).
Each root becomes a `-L` flag. Collisions inside one library are analysis
errors; across libraries, the first root wins. `JqInfo.transitive_srcs` contains
the staged tree artifacts holding the transitive module files, not the original
unstaged sources; individual children of a tree artifact are not analysis-time
Files. `DefaultInfo.files` contains the library's own staged root.

## Executables

```starlark
jq_binary(
    name = "notice",
    main = "notice.jq",  # Exactly one of main or filter.
    deps = [":strings"],
    args = ["-r"],
    named_srcs = {"config": ":config.json"},
    data = [],
)
```

The executable resolves jq, module roots, the main file, and named inputs through
Bazel runfiles. Named inputs become `--slurpfile name path`. Flags in `args`
precede the filter; runtime positional inputs follow it. The executable forwards
`JqInfo` and works with `bazel run`, shell tests, genrule `tools`, and rules
accepting executable tools.

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

`jq_test` defaults to `size = "small"` and forwards common `sh_test` attributes
such as `tags`, `timeout`, and `visibility`.

* **Assertion:** specify `filter` or `main`. Runs with `-e`, so a final `false`,
  `null`, no output, or jq error fails. `srcs` become positional inputs; without
  them, `-n` is added. Named inputs can compare documents:
  `named_srcs = {"a": ":a.json", "b": ":b.json"}`,
  `filter = "$a[0] == $b[0]"`.
* **Golden:** additionally set `expected`. Both actual and expected output are
  normalized through `jq -S .` and compared with a readable diff. With
  `raw = True`, output is compared byte-for-byte instead. This mode does not
  add `-e`, so valid `false` and `null` outputs can be golden values.
* **Cases:** specify only `cases` and optional `deps`/test attributes. This runs
  jq's native `--run-tests` backend, without a YAML parser.

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

Run the rules' own tests from the `bazel/` module root:
`bazel test //jq/...`.
