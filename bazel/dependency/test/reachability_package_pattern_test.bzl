load("@bazel_skylib//lib:unittest.bzl", "asserts", "unittest")
load("//dependency:reachability.bzl", "package_pattern_matches")

def _reachability_package_pattern_test_impl(ctx):
    env = unittest.begin(ctx)

    asserts.true(
        env,
        package_pattern_matches(
            "//dependency/test/transitive/ext/direct",
            "//dependency/test/transitive/ext/...",
        ),
    )
    asserts.true(
        env,
        package_pattern_matches(
            "//dependency/test/transitive/ext",
            "//dependency/test/transitive/ext/...",
        ),
    )
    asserts.true(
        env,
        package_pattern_matches(
            "//dependency/test/transitive/ext/direct",
            "//dependency/test/transitive/ext/direct",
        ),
    )
    asserts.false(
        env,
        package_pattern_matches(
            "//dependency/test/transitive/shared",
            "//dependency/test/transitive/ext/...",
        ),
    )

    return unittest.end(env)

reachability_package_pattern_test = unittest.make(_reachability_package_pattern_test_impl)
