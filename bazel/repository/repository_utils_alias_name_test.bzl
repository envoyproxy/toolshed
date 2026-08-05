load("@bazel_skylib//lib:unittest.bzl", "asserts", "unittest")
load("//bazel/repository:utils.bzl", "_alias_name")

def _alias_name_test_impl(ctx):
    env = unittest.begin(ctx)

    asserts.equals(env, "clang_platform", _alias_name("clang_platform"))
    asserts.equals(env, "clang_platform", _alias_name("+envoy_toolchains_extension+clang_platform"))
    asserts.equals(env, "clang_platform", _alias_name("module+ext+clang_platform"))
    asserts.equals(env, "clang_platform", _alias_name("module++ext++clang_platform"))
    asserts.equals(env, "clang_platform", _alias_name("module~~ext~~clang_platform"))
    asserts.equals(env, "clang_platform", _alias_name("module~ext~clang_platform"))

    return unittest.end(env)

alias_name_test = unittest.make(_alias_name_test_impl)
