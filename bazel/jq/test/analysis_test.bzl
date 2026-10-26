"""Provider, ordering, and invalid-attribute analysis tests."""

load("@bazel_skylib//lib:unittest.bzl", "analysistest", "asserts")
load("//jq:defs.bzl", "JqInfo")

def _provider_test_impl(ctx):
    env = analysistest.begin(ctx)
    target = analysistest.target_under_test(env)
    asserts.true(env, JqInfo in target)
    info = target[JqInfo]
    asserts.equals(env, ctx.attr.roots, [root.basename for root in info.roots.to_list()])
    asserts.equals(env, sorted(ctx.attr.roots), sorted([src.basename for src in info.transitive_srcs.to_list()]))
    asserts.true(env, all([root.is_directory for root in info.roots.to_list()]))
    return analysistest.end(env)

provider_test = analysistest.make(
    _provider_test_impl,
    attrs = {"roots": attr.string_list()},
)

def _failure_test_impl(ctx):
    env = analysistest.begin(ctx)
    asserts.expect_failure(env, ctx.attr.message)
    return analysistest.end(env)

failure_test = analysistest.make(
    _failure_test_impl,
    expect_failure = True,
    attrs = {"message": attr.string()},
)

def _collision_source_impl(ctx):
    # A generated and a checked-in File can have the same short_path.
    output = ctx.actions.declare_file("str.jq")
    ctx.actions.write(output, "def trim: .;")
    return [DefaultInfo(files = depset([output]))]

collision_source = rule(implementation = _collision_source_impl)
