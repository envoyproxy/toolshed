"""Analysis coverage for generated_certs."""

load("@bazel_skylib//lib:unittest.bzl", "analysistest", "asserts")

def _command_test_impl(ctx):
    env = analysistest.begin(ctx)
    actions = analysistest.target_actions(env)
    actions = [action for action in actions if action.mnemonic == "Genrule"]
    asserts.equals(env, 1, len(actions))
    command = " ".join(actions[0].argv)
    asserts.true(env, ctx.attr.expected in command, "missing command fragment: " + ctx.attr.expected)
    return analysistest.end(env)

command_test = analysistest.make(
    _command_test_impl,
    attrs = {"expected": attr.string(mandatory = True)},
)
