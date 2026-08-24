load("@bazel_skylib//lib:unittest.bzl", "asserts", "unittest")
load("//dependency:reachability.bzl", "merge_defines")

def _reachability_merge_defines_test_impl(ctx):
    env = unittest.begin(ctx)

    merged = merge_defines(
        [
            "existing=old",
            "skipmalformed",
            "override=old",
        ],
        {
            "//dependency/test:reachability_mode": "extra",
            "override": "new",
            "added": "value",
        },
    )
    asserts.equals(
        env,
        ["added=value", "existing=old", "override=new"],
        merged,
    )

    return unittest.end(env)

reachability_merge_defines_test = unittest.make(_reachability_merge_defines_test_impl)
