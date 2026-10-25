"""Analysis regressions for repository-relative compiler and header paths."""

load("@bazel_skylib//lib:unittest.bzl", "analysistest", "asserts")
load("@rules_cc//cc/common:cc_common.bzl", "cc_common")

def _gcc_paths_test_impl(ctx):
    env = analysistest.begin(ctx)
    toolchain = analysistest.target_under_test(env)[cc_common.CcToolchainInfo]
    compiler = ctx.file.compiler.path
    root = compiler[:-len("/xbin/gcc")]
    sysroot = ctx.file.sysroot.path
    asserts.equals(env, compiler, toolchain.compiler_executable)
    asserts.equals(env, root + "/xbin/ar", toolchain.ar_executable)
    for directory in toolchain.built_in_include_directories:
        asserts.true(
            env,
            directory.startswith(root + "/") or directory.startswith(sysroot + "/"),
            "Unexpected builtin include directory: " + directory,
        )
        asserts.false(env, directory.count("external/") > 1, "Repository prefix duplicated: " + directory)
    return analysistest.end(env)

gcc_paths_test = analysistest.make(
    _gcc_paths_test_impl,
    attrs = {
        "compiler": attr.label(allow_single_file = True),
        "sysroot": attr.label(allow_single_file = True),
    },
)
