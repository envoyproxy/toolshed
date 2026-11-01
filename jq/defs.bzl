"""Macros for consuming `envoy_toolshed_jq` modules from Bazel.

`toolshed_jq` runs jq at build time through `rules_jq`, with this module's
`*.jq` files (`//:library`) on its search path, so callers can
`import`/`include` them by their scoped path, eg:

```starlark
load("@envoy_toolshed_jq//:defs.bzl", "toolshed_jq")

toolshed_jq(
    name = "notice",
    srcs = ["event.json"],
    filter = "import \"github/actions\" as github; github::log_bubble({...})",
)
```

`jq_module_test` wraps one `jq/tests/<scope>/<module>/` directory of
`.test.yml` cases as an `sh_test`, running `run-tests.sh` through the
hermetic aspect jq/yq toolchains (the same script also runs bare, outside
Bazel, as `./jq/run-tests.sh`).

`test_modules` derives the list of `<scope>/<module>` directories that have
`.test.yml` cases, so `jq/BUILD` doesn't have to hand-maintain it.
"""

load("@bazel_skylib//lib:shell.bzl", "shell")
load("@rules_jq//jq:defs.bzl", "jq_binary")
load("@rules_shell//shell:sh_test.bzl", "sh_test")

# These must be `Label()`s: plain strings resolve in the *caller's* repo, so
# `toolshed_jq` used from another module would look for them there instead of
# here.
_LIBRARY = Label("//:library")
_MODULES = Label("//:modules")
_RUN_TESTS = Label("//:run-tests.sh")

def toolshed_jq(name, srcs, filter_file = None, filter = None, args = [], data = [], out = None, **kwargs):
    """Run jq at build time with a filter that can import `envoy_toolshed_jq` modules.

    A `rules_jq` `jq_binary` over this module's `jq_library` (`//:library`),
    run by a genrule that writes its output to `out`, so filters can do eg
    `import "str" as str;` or `import "github/gfm" as gfm;`.

    Args:
        name: Name of the rule.
        srcs: List of input files, passed to jq after `args`. May be empty, in
            which case jq runs with `--null-input`.
        filter: Filter expression, mutually exclusive with `filter_file`. With
            neither, the identity filter (`.`).
        filter_file: `.jq` file containing the filter.
        args: Additional args to pass to jq, after the filter. `$(location)`
            and other genrule expansions apply.
        data: Additional files referenced from `args`.
        out: Output file; defaults to `<name>.json`.
        **kwargs: Other common named parameters such as `tags` or
            `visibility`, passed through to the genrule.
    """
    binary = name + "_jq"
    null_input = not srcs and "-n" not in args and "--null-input" not in args
    jq_binary(
        name = binary,
        main = filter_file,
        # As with `jq()`, no filter means the identity filter, not a
        # pass-through jq taking its program from the arguments.
        filter = filter or ("" if filter_file else "."),
        deps = [_LIBRARY],
        jq_args = ["-n"] if null_input else [],
        tags = ["manual"],
        testonly = kwargs.get("testonly", False),
        visibility = ["//visibility:private"],
    )
    native.genrule(
        name = name,
        srcs = srcs + data,
        outs = [out or name + ".json"],
        cmd = " ".join(
            ["$(execpath :%s)" % binary] +
            [shell.quote(arg) for arg in args] +
            ["$(execpaths %s)" % src for src in srcs] +
            ["> $@"],
        ),
        tools = [":" + binary],
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
        srcs = [_RUN_TESTS],
        args = ["tests/%s" % module],
        data = [
            _RUN_TESTS,
            _MODULES,
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

def test_modules(test_files):
    """Derive `<scope>/<module>` test-directory names from `.test.yml` paths.

    Args:
        test_files: A list of `tests/**/*.test.yml`-relative paths, eg from
            `glob(["tests/**/*.test.yml"])`.

    Returns:
        A sorted list of unique `<scope>/<module>` directories relative to
        `tests/`, eg `["args", "bazel/aquery", "github/gfm", ...]`, suitable
        for passing to `jq_module_test`'s `module` arg.
    """
    modules = {}
    for test_file in test_files:
        # eg "tests/bazel/aquery/frag_path.test.yml" -> "bazel/aquery"
        rest = test_file[len("tests/"):]
        modules["/".join(rest.split("/")[:-1])] = None
    return sorted(modules.keys())
