"""Macros for consuming `envoy_toolshed_jq` modules from Bazel.

`toolshed_jq` wraps `@aspect_bazel_lib//lib:jq.bzl`'s `jq()`, adding a `-L`
flag that points at the directory containing this module's `*.jq` files, so
callers can `import`/`include` them by their scoped path, eg:

```starlark
load("@envoy_toolshed_jq//:defs.bzl", "toolshed_jq")

toolshed_jq(
    name = "notice",
    srcs = ["event.json"],
    filter = "import \"github/github\" as github; github::log_bubble({...})",
)
```

`jq_module_test` wraps one `jq/tests/<scope>/<module>/` directory of
`.test.yml` cases as an `sh_test`, running `run-tests.sh` through the
hermetic aspect jq/yq toolchains (the same script also runs bare, outside
Bazel, as `./jq/run-tests.sh`).
"""

load("@aspect_bazel_lib//lib:jq.bzl", _jq = "jq")
load("@rules_shell//shell:sh_test.bzl", "sh_test")

# A stable, single-file target at the module root. Its containing directory
# (via `$(dirname $(execpath ...))`, resolved by the shell that
# `@aspect_bazel_lib`'s `jq()` runs its command in) is the `-L` search
# directory for the modules in this repo.
_MODULES_ROOT_MARKER = "//:modules_root.marker"

def toolshed_jq(name, srcs, filter_file = None, filter = None, args = [], data = [], **kwargs):
    """Invoke jq with a filter that can import/include `envoy_toolshed_jq` modules.

    This is a thin wrapper around `@aspect_bazel_lib//lib:jq.bzl`'s `jq()`
    that adds `-L <modules root>` to `args` and this repo's `.jq` modules to
    `data`, so filters can do eg `import "str" as str;` or
    `import "github/gfm" as gfm;`.

    Args:
        name: Name of the rule.
        srcs: List of input files. May be empty.
        filter: Filter expression, mutually exclusive with `filter_file`.
        filter_file: File containing the filter expression.
        args: Additional args to pass to jq (the `-L <modules root>` flag is
            added automatically).
        data: Additional data files jq may need at runtime (this repo's
            modules are added automatically).
        **kwargs: Other common named parameters such as `out`, `tags` or
            `visibility`, passed through to `jq()`.
    """
    _jq(
        name = name,
        srcs = srcs,
        filter = filter,
        filter_file = filter_file,
        args = args + [
            "-L",
            "$(dirname $(execpath %s))" % _MODULES_ROOT_MARKER,
        ],
        data = data + ["//:modules", _MODULES_ROOT_MARKER],
        expand_args = True,
        **kwargs
    )

def jq_module_test(name, module, size = "small", **kwargs):
    """Run the `.test.yml` cases in `jq/tests/<module>/` as an `sh_test`.

    `module` is the test subdirectory relative to `jq/tests`, eg
    `"github/gfm"` for the cases in `jq/tests/github/gfm/`.

    Args:
        name: Name of the test rule.
        module: Test subdirectory under `tests/`, eg `"str"` or `"github/gfm"`.
        size: `sh_test` size, defaults to `"small"`.
        **kwargs: Other common named parameters such as `tags`, passed
            through to `sh_test`.
    """
    sh_test(
        name = name,
        size = size,
        srcs = ["//:run-tests.sh"],
        args = ["tests/%s" % module],
        data = [
            "//:run-tests.sh",
            "//:modules",
            "@jq_toolchains//:resolved_toolchain",
            "@yq_toolchains//:resolved_toolchain",
        ] + native.glob(["tests/%s/**" % module]),
        deps = ["@bazel_tools//tools/bash/runfiles"],
        env = {
            "JQ_BIN": "$(rlocationpath @jq_toolchains//:resolved_toolchain)",
            "YQ_BIN": "$(rlocationpath @yq_toolchains//:resolved_toolchain)",
        },
        **kwargs
    )
