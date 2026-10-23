load("@bazel_skylib//lib:unittest.bzl", "asserts", "unittest")
load("@llvm_toolchain_llvm//:llvm.bzl", "LLVM_IS_HOST", "LLVM_LIB_DIR", "LLVM_MAJOR", "LLVM_MAJOR_MINOR", "LLVM_VERSION")
load("//compile:llvm_minimal.bzl", "parse_clang_version")

def _clang_version_test_impl(ctx):
    env = unittest.begin(ctx)

    asserts.equals(env, "22.1.8", parse_clang_version("clang version 22.1.8"))
    asserts.equals(env, "22.1.8", parse_clang_version("Ubuntu clang version 22.1.8-1ubuntu1"))
    asserts.equals(env, "22.1.8", parse_clang_version("clang version 22.1.8 (https://example.invalid)"))
    asserts.equals(env, "", parse_clang_version("clang version unknown"))

    return unittest.end(env)

clang_version_test = unittest.make(_clang_version_test_impl)

def _llvm_metadata_test_impl(ctx):
    env = unittest.begin(ctx)

    asserts.equals(env, "22.1.8", LLVM_VERSION)
    asserts.equals(env, "22", LLVM_MAJOR)
    asserts.equals(env, "22.1", LLVM_MAJOR_MINOR)
    asserts.equals(env, "lib", LLVM_LIB_DIR)
    asserts.equals(env, False, LLVM_IS_HOST)

    return unittest.end(env)

llvm_metadata_test = unittest.make(_llvm_metadata_test_impl)
