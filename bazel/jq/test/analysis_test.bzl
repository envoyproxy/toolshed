"""Provider, ordering, and invalid-attribute analysis tests."""

load("@bazel_skylib//lib:unittest.bzl", "analysistest", "asserts", "unittest")
load("//jq:defs.bzl", "JqInfo", "jq_test")

def _provider_test_impl(ctx):
    env = analysistest.begin(ctx)
    target = analysistest.target_under_test(env)
    asserts.true(env, JqInfo in target)
    info = target[JqInfo]
    asserts.equals(env, ctx.attr.roots, [root.basename for root in info.roots.to_list()])
    asserts.equals(env, sorted(ctx.attr.sources), sorted([src.basename for src in info.transitive_srcs.to_list()]))
    asserts.true(env, all([not src.is_directory for src in info.transitive_srcs.to_list()]))
    asserts.true(env, all([root.is_directory for root in info.roots.to_list()]))
    return analysistest.end(env)

provider_test = analysistest.make(
    _provider_test_impl,
    attrs = {"roots": attr.string_list(), "sources": attr.string_list()},
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

def _constraints_test_impl(ctx):
    env = unittest.begin(ctx)
    asserts.equals(env, [], ctx.attr.missing)
    return unittest.end(env)

_constraints_test = unittest.make(
    _constraints_test_impl,
    attrs = {"missing": attr.string_list()},
)

def execution_constraints_test(name):
    """Check that every test backend forwards toolchain platform constraints.

    Args:
        name: Test target name and prefix for manual inspection fixtures.
    """
    missing = []
    for mode, options in {
        "assertion": {"filter": "true"},
        "golden": {"filter": ".", "expected": "answer.json"},
        "cases": {"cases": "str.test"},
    }.items():
        fixture = name + "_" + mode
        jq_test(
            name = fixture,
            exec_compatible_with = [Label("//jq/test:execution_constraint")],
            exec_properties = {"jq_test_property": "value"},
            target_compatible_with = [Label("//jq/test:execution_constraint")],
            tags = ["manual"],
            **options
        )
        outer = native.existing_rule(fixture)
        if outer["kind"] != "_runner_test":
            missing.append(fixture + ": not a direct test rule")
        if native.existing_rule(fixture + "_runner") != None:
            missing.append(fixture + ": unexpected runner helper")
        for attribute, expected in {
            "exec_compatible_with": (":execution_constraint",),
            "exec_properties": {"jq_test_property": "value"},
            "target_compatible_with": (":execution_constraint",),
        }.items():
            if outer[attribute] != expected:
                missing.append(fixture + ": " + attribute)
        helper = native.existing_rule(fixture + "_binary")
        if mode == "cases":
            if helper != None:
                missing.append(fixture + ": unexpected binary helper")
        else:
            for attribute in ["exec_compatible_with", "exec_properties", "target_compatible_with", "tags"]:
                if helper[attribute] != outer[attribute]:
                    missing.append(fixture + "_binary: " + attribute)
            if not helper["testonly"]:
                missing.append(fixture + "_binary: testonly")
    _constraints_test(name = name, missing = missing)
