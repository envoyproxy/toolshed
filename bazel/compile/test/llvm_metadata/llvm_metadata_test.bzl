load("@bazel_skylib//lib:unittest.bzl", "asserts", "unittest")
load("@llvm_toolchain_llvm//:llvm.bzl", "LLVM_IS_HOST", "LLVM_LIB_DIR", "LLVM_MAJOR", "LLVM_MAJOR_MINOR", "LLVM_VERSION")
load("//:versions.bzl", EXPECTED_LLVM_VERSION = "LLVM_VERSION")

def _llvm_metadata_test_impl(ctx):
    env = unittest.begin(ctx)

    asserts.equals(env, EXPECTED_LLVM_VERSION, LLVM_VERSION)
    asserts.equals(env, EXPECTED_LLVM_VERSION.split(".")[0], LLVM_MAJOR)
    asserts.equals(env, ".".join(EXPECTED_LLVM_VERSION.split(".")[:2]), LLVM_MAJOR_MINOR)
    asserts.equals(env, "lib", LLVM_LIB_DIR)
    asserts.equals(env, False, LLVM_IS_HOST)

    return unittest.end(env)

llvm_metadata_test = unittest.make(_llvm_metadata_test_impl)
