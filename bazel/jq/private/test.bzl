"""Assertion, golden, and native case-file tests for jq."""

load("@rules_shell//shell:sh_test.bzl", "sh_test")
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
        command = "exec %s --run-tests %s" % (command, location(ctx, ctx.file.cases))
    else:
        dependencies.append(ctx.attr.binary)
        files.append(ctx.executable.binary)
        invocation = location(ctx, ctx.executable.binary)
        for src in ctx.files.srcs:
            invocation += " " + location(ctx, src)
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
    return [launcher(ctx, command, files, dependencies)]

_test_runner = rule(
    implementation = _test_runner_impl,
    executable = True,
    attrs = {
        "binary": attr.label(executable = True, cfg = "target"),
        "cases": attr.label(allow_single_file = True),
        "srcs": attr.label_list(allow_files = True),
        "expected": attr.label(allow_single_file = True),
        "raw": attr.bool(),
        "deps": attr.label_list(providers = [JqInfo]),
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
        args = [],
        expected = None,
        raw = False,
        cases = None,
        data = [],
        size = "small",
        **kwargs):
    """Test a jq assertion, compare a golden output, or run native jq cases.

    With no input srcs, assertion and golden modes add -n. Only assertion
    mode adds -e. Golden JSON is normalized using jq -S unless raw is true.
    Common sh_test attributes such as tags, timeout, and visibility pass through.

    Args:
        name: Test target name.
        main: Main .jq file, mutually exclusive with filter.
        filter: Inline jq program, mutually exclusive with main.
        deps: Targets providing JqInfo.
        named_srcs: Mapping from variable names to single-file slurpfile labels.
        srcs: Positional JSON input files.
        args: Additional jq flags.
        expected: Golden output file, selecting golden mode.
        raw: Compare golden files byte-for-byte rather than normalizing JSON.
        cases: Native jq case file, mutually exclusive with assertion/golden options.
        data: Additional runtime files and targets.
        size: Bazel test size, defaulting to small.
        **kwargs: Common sh_test attributes.
    """
    if cases != None and (main != None or filter or named_srcs or srcs or args or expected != None or raw):
        fail("cases mode is mutually exclusive with main/filter, named_srcs, srcs, args, expected, and raw")
    if raw and expected == None:
        fail("raw requires expected")
    common = {
        "testonly": True,
        "tags": kwargs.get("tags", []),
        "visibility": ["//visibility:private"],
    }
    for attribute in ["exec_compatible_with", "exec_properties", "target_compatible_with"]:
        if attribute in kwargs:
            common[attribute] = kwargs[attribute]
    binary = None
    if cases == None:
        binary = name + "_binary"
        jq_binary(
            name = binary,
            main = main,
            filter = filter,
            deps = deps,
            named_srcs = named_srcs,
            args = args + ([] if srcs else ["-n"]) + (["-e"] if expected == None else []),
            data = data,
            **common
        )
        binary = ":" + binary
    runner = name + "_runner"
    _test_runner(
        name = runner,
        binary = binary,
        cases = cases,
        deps = deps,
        srcs = srcs,
        expected = expected,
        raw = raw,
        **common
    )
    sh_test(
        name = name,
        srcs = [":" + runner],
        data = data,
        size = size,
        **kwargs
    )
