load("@bazel_skylib//lib:unittest.bzl", "asserts", "unittest")
load("//repository:utils.bzl", "alias_name")

def _alias_name_test_impl(ctx):
    env = unittest.begin(ctx)

    asserts.equals(env, "clang_platform", alias_name("clang_platform"))
    asserts.equals(env, "clang_platform", alias_name("+envoy_toolchains_extension+clang_platform"))
    asserts.equals(env, "clang_platform", alias_name("module+ext+clang_platform"))
    asserts.equals(env, "clang_platform", alias_name("module++ext++clang_platform"))
    asserts.equals(env, "clang_platform", alias_name("module~~ext~~clang_platform"))
    asserts.equals(env, "clang_platform", alias_name("module~ext~clang_platform"))

    return unittest.end(env)

alias_name_test = unittest.make(_alias_name_test_impl)
