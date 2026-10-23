load("@bazel_skylib//lib:unittest.bzl", "asserts", "unittest")
load("//compile:llvm_minimal.bzl", "parse_clang_version")

def _clang_version_test_impl(ctx):
    env = unittest.begin(ctx)

    asserts.equals(env, "22.1.8", parse_clang_version("clang version 22.1.8"))
    asserts.equals(env, "22.1.8", parse_clang_version("Ubuntu clang version 22.1.8-1ubuntu1"))
    asserts.equals(env, "22.1.8", parse_clang_version("clang version 22.1.8 (https://example.invalid)"))
    asserts.equals(env, "", parse_clang_version("clang version unknown"))

    return unittest.end(env)

clang_version_test = unittest.make(_clang_version_test_impl)
