"""Analysis regressions for repository-relative compiler and header paths."""

load("@bazel_skylib//lib:unittest.bzl", "analysistest", "asserts")
load("@rules_cc//cc/common:cc_common.bzl", "cc_common")
load("@rules_cc//cc/common:cc_info.bzl", "CcInfo")

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

def _gcc_runtime_test_impl(ctx):
    env = analysistest.begin(ctx)
    info = analysistest.target_under_test(env)[CcInfo]
    root = ctx.file.compiler.path[:-len("/xbin/gcc")]
    prefix = root + ("/aarch64-linux" if ctx.attr.arch == "aarch64" else "")
    include = prefix + "/include/c++/" + ctx.attr.version
    includes = info.compilation_context.system_includes.to_list()
    for directory in [include, include + "/" + ctx.attr.arch + "-linux", include + "/backward"]:
        asserts.true(env, directory in includes, "Missing repository-rooted C++ include: " + directory)
    all_includes = includes + info.compilation_context.includes.to_list() + info.compilation_context.quote_includes.to_list()
    for directory in all_includes:
        # cc_library also supplies bin/genfiles variants of repository paths.
        repository_path = directory == root or directory.startswith(root + "/")
        generated_path = directory.startswith("bazel-out/") and (
            directory.endswith("/" + root) or ("/" + root + "/") in directory
        )
        asserts.true(env, repository_path or generated_path, "Include directory escapes GCC repository: " + directory)
        asserts.false(env, directory.count("external/") > 1, "Repository prefix duplicated: " + directory)
    libraries = []
    for linker_input in info.linking_context.linker_inputs.to_list():
        inputs = linker_input.libraries
        libraries.extend(inputs.to_list() if type(inputs) == "depset" else inputs)
    asserts.equals(env, 1, len(libraries))
    for library in libraries:
        asserts.equals(env, prefix + "/lib64/libstdc++.a", library.static_library.path)
        asserts.equals(env, None, library.dynamic_library)
        asserts.equals(env, None, library.interface_library)
    gcc_lib = root + "/lib/gcc/" + ctx.attr.arch + "-linux/" + ctx.attr.version
    asserts.equals(
        env,
        [gcc_lib + "/libgcc.a", gcc_lib + "/libgcc_eh.a"],
        sorted([file.path for file in ctx.attr.libgcc[DefaultInfo].files.to_list()]),
    )
    return analysistest.end(env)

gcc_runtime_test = analysistest.make(
    _gcc_runtime_test_impl,
    attrs = {
        "arch": attr.string(mandatory = True),
        "compiler": attr.label(allow_single_file = True),
        "libgcc": attr.label(mandatory = True),
        "version": attr.string(mandatory = True),
    },
)
