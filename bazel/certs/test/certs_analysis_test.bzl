"""Analysis coverage for generated_certs."""

load("@bazel_skylib//lib:unittest.bzl", "analysistest", "asserts")

def _command_test_impl(ctx):
    env = analysistest.begin(ctx)
    actions = analysistest.target_actions(env)
    actions = [action for action in actions if action.mnemonic == "Genrule"]
    asserts.equals(env, 1, len(actions))
    command = " ".join(actions[0].argv)
    asserts.true(
        env,
        ctx.attr.expected in command,
        "missing command fragment: " + ctx.attr.expected,
    )
    return analysistest.end(env)

command_test = analysistest.make(
    _command_test_impl,
    attrs = {"expected": attr.string(mandatory = True)},
)

def _files_test_impl(ctx):
    env = analysistest.begin(ctx)
    files = sorted([
        f.basename
        for f in analysistest.target_under_test(env)[DefaultInfo].files.to_list()
    ])

    if ctx.attr.expected:
        asserts.equals(env, ctx.attr.expected, files)

    for f in files:
        for suffix in ctx.attr.forbidden_suffixes:
            asserts.false(
                env,
                f.endswith(suffix),
                f + " unexpectedly ends with " + suffix,
            )

    return analysistest.end(env)

files_test = analysistest.make(
    _files_test_impl,
    attrs = {
        "expected": attr.string_list(),
        "forbidden_suffixes": attr.string_list(),
    },
)
