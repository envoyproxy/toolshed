"""Assertion, golden, and native case-file tests for jq."""

load(":binary.bzl", "jq_binary", "jq_command", "jq_info", "launcher", "location")
load(":providers.bzl", "JQ_TOOLCHAIN_TYPE", "JqInfo")

def _test_runner_impl(ctx):
    info = jq_info(ctx.attr.deps)
    roots = info.roots.to_list()
    jq, command = jq_command(ctx, roots)
    files = [jq] + roots + ctx.files.srcs
    dependencies = ctx.attr.deps[:]
    if ctx.file.cases:
        files.append(ctx.file.cases)
        command = 'exec %s --run-tests %s "$@"' % (command, location(ctx, ctx.file.cases))
    else:
        dependencies.append(ctx.attr.binary)
        files.append(ctx.executable.binary)
        invocation = location(ctx, ctx.executable.binary)
        for src in ctx.files.srcs:
            invocation += " " + location(ctx, src)
        invocation += ' "$@"'
        if ctx.file.expected:
            files.append(ctx.file.expected)
            expected = location(ctx, ctx.file.expected)
            command = '%s > "$TEST_TMPDIR/actual"\n' % invocation
            if ctx.attr.raw:
                command += 'diff -u %s "$TEST_TMPDIR/actual"' % expected
            else:
                command += '%s -S . %s > "$TEST_TMPDIR/expected.json"\n' % (location(ctx, jq), expected)
                command += '%s -S . "$TEST_TMPDIR/actual" > "$TEST_TMPDIR/actual.json"\n' % location(ctx, jq)
                command += 'diff -u "$TEST_TMPDIR/expected.json" "$TEST_TMPDIR/actual.json"'
        else:
            command = "exec " + invocation
    return [
        launcher(ctx, command, files + ctx.files.data, dependencies + ctx.attr.data),
        testing.TestEnvironment(
            environment = {
                key: ctx.expand_make_variables("env", ctx.expand_location(value, targets = ctx.attr.data), {})
                for key, value in ctx.attr.env.items()
            },
            inherited_environment = ctx.attr.env_inherit,
        ),
    ]

_runner_test = rule(
    implementation = _test_runner_impl,
    test = True,
    attrs = {
        "binary": attr.label(executable = True, cfg = "target"),
        "cases": attr.label(allow_single_file = True),
        "srcs": attr.label_list(allow_files = True),
        "expected": attr.label(allow_single_file = True),
        "raw": attr.bool(),
        "deps": attr.label_list(providers = [JqInfo]),
        "data": attr.label_list(allow_files = True),
        "env": attr.string_dict(),
        "env_inherit": attr.string_list(),
        "_launcher": attr.label(default = Label("//jq/private:launcher.sh.tpl"), allow_single_file = True),
        "_runfiles": attr.label(default = Label("@bazel_tools//tools/bash/runfiles")),
    },
    toolchains = [JQ_TOOLCHAIN_TYPE],
)

def jq_test(
        name,
        main = None,
        filter = "",
        deps = [],
        named_srcs = {},
        srcs = [],
        jq_args = [],
        expected = None,
        raw = False,
        cases = None,
        data = [],
        size = "small",
        **kwargs):
    """Test a jq assertion, compare a golden output, or run native jq cases.

    With no input srcs or args, assertion and golden modes add -n. Only assertion
    mode adds -e. Golden JSON is normalized using jq -S unless raw is true.
    Common test attributes such as tags, timeout, and visibility pass through.

    Args:
        name: Test target name.
        main: Main .jq file, mutually exclusive with filter.
        filter: Inline jq program, mutually exclusive with main.
        deps: Targets providing JqInfo.
        named_srcs: Mapping from variable names to single-file slurpfile labels.
        srcs: Positional JSON input files.
        jq_args: Additional jq flags.
        expected: Golden output file, selecting golden mode.
        raw: Compare golden files byte-for-byte rather than normalizing JSON.
        cases: Native jq case file, mutually exclusive with assertion/golden options.
        data: Additional runtime files and targets.
        size: Bazel test size, defaulting to small.
        **kwargs: Common test attributes, including positional args and env.
    """
    if cases != None and (main != None or filter or named_srcs or srcs or jq_args or expected != None or raw):
        fail("cases mode is mutually exclusive with main/filter, named_srcs, srcs, jq_args, expected, and raw")
    if raw and expected == None:
        fail("raw requires expected")
    binary = None
    if cases == None:
        binary = name + "_binary"
        jq_binary(
            name = binary,
            main = main,
            filter = filter,
            deps = deps,
            named_srcs = named_srcs,
            jq_args = jq_args + ([] if srcs or kwargs.get("args") else ["-n"]) + (["-e"] if expected == None else []),
            data = data,
            testonly = True,
            tags = kwargs.get("tags", []),
            visibility = ["//visibility:private"],
            exec_compatible_with = kwargs.get("exec_compatible_with", []),
            exec_properties = kwargs.get("exec_properties", {}),
            target_compatible_with = kwargs.get("target_compatible_with", []),
        )
        binary = ":" + binary
    _runner_test(
        name = name,
        binary = binary,
        cases = cases,
        deps = deps,
        srcs = srcs,
        expected = expected,
        raw = raw,
        data = data,
        size = size,
        **kwargs
    )
