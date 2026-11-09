"""jq with the toolshed modules importable, for WORKSPACE builds.

This is the WORKSPACE counterpart of `envoy_toolshed_jq`'s `defs.bzl` on
`main`. It provides the same `toolshed_jq` macro and a `jq` executable with
the modules on its search path, but resolves jq from the `aspect_bazel_lib`
toolchain rather than through `rules_jq`.

Load it from the `envoy_toolshed_jq` repository that `setup_sq()` creates, so
labels match `main`:

```starlark
load("@envoy_toolshed_jq//:defs.bzl", "toolshed_jq")

toolshed_jq(
    name = "deps",
    srcs = ["deps.json"],
    filter = "import \"cve/utils\" as utils; utils::parse_deps(.)",
)
```
"""

load("@bazel_skylib//lib:shell.bzl", "shell")
load("@bazel_skylib//rules:write_file.bzl", "write_file")

_JQ_TOOLCHAIN_TYPE = "@aspect_bazel_lib//lib:jq_toolchain_type"

# These are relative to this file's package, so they resolve in whichever
# repository it is loaded from.
_JQ = Label(":jq")
_LAUNCHER = Label(":launcher.sh.tpl")
_MODULES = Label(":modules")
_MODULES_ROOT = Label(":modules_root.marker")

# Forward the launcher's positional arguments. `"$@"` alone is an unbound
# variable under `set -u` in bash < 4.4 (macOS ships 3.2) when argv is empty.
_ARGV = '${1+"$@"}'

def _runfile_path(ctx, file):
    if file.short_path.startswith("../"):
        return file.short_path[3:]
    return "%s/%s" % (ctx.workspace_name, file.short_path)

def _jq_binary_impl(ctx):
    jq = ctx.toolchains[_JQ_TOOLCHAIN_TYPE].jqinfo.bin
    output = ctx.actions.declare_file(ctx.label.name + ".sh")

    # A plain assignment aborts under `set -e` when jq_root fails, whereas a
    # `$(...)` in argument position would not.
    command = 'JQ_ROOT="$(jq_root %s)"\nexec "$(rlocation %s)" -L "$JQ_ROOT" %s' % (
        shell.quote(_runfile_path(ctx, ctx.file.modules_root)),
        shell.quote(_runfile_path(ctx, jq)),
        _ARGV,
    )
    ctx.actions.expand_template(
        template = ctx.file._launcher,
        output = output,
        substitutions = {"@@COMMAND@@": command},
        is_executable = True,
    )
    return [DefaultInfo(
        executable = output,
        runfiles = ctx.runfiles(files = [jq, ctx.file.modules_root] + ctx.files.modules),
    )]

jq_binary = rule(
    implementation = _jq_binary_impl,
    doc = "jq itself, with the toolshed modules on its search path.",
    executable = True,
    attrs = {
        "modules": attr.label(default = _MODULES, allow_files = True),
        "modules_root": attr.label(default = _MODULES_ROOT, allow_single_file = True),
        "_launcher": attr.label(default = _LAUNCHER, allow_single_file = True),
    },
    toolchains = [_JQ_TOOLCHAIN_TYPE],
)

def toolshed_jq(name, srcs, filter_file = None, filter = None, args = [], data = [], out = None, **kwargs):
    """Run jq at build time with a filter that can import the toolshed modules.

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
    if filter_file and filter:
        fail("toolshed_jq accepts at most one of filter_file or filter")
    if not filter_file:
        # Written to a file rather than quoted into the command, so the filter
        # is not subject to genrule `$` expansion.
        filter_file = name + "_filter.jq"
        write_file(
            name = name + "_filter",
            out = filter_file,
            content = [filter or "."],
            tags = ["manual"],
            testonly = kwargs.get("testonly", False),
            visibility = ["//visibility:private"],
        )
    native.genrule(
        name = name,
        srcs = srcs + data + [filter_file],
        outs = [out or name + ".json"],
        cmd = " ".join(
            ["$(execpath %s)" % _JQ] +
            # Without `srcs`, always read no input.
            ([] if srcs else ["-n"]) +
            ["-f", "$(execpath %s)" % filter_file] +
            [shell.quote(arg) for arg in args] +
            ["$(execpaths %s)" % src for src in srcs] +
            ["> $@"],
        ),
        tools = [_JQ],
        **kwargs
    )
