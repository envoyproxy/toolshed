"""Analysis regressions for repository-relative compiler and header paths."""

load("@bazel_skylib//lib:unittest.bzl", "analysistest", "asserts")
load("@rules_cc//cc:action_names.bzl", "ACTION_NAMES")
load("@rules_cc//cc/common:cc_common.bzl", "cc_common")
load("@rules_cc//cc/common:cc_info.bzl", "CcInfo")

def _link_configuration(ctx, toolchain):
    features = cc_common.configure_features(ctx = ctx, cc_toolchain = toolchain)
    variables = cc_common.create_link_variables(
        cc_toolchain = toolchain,
        feature_configuration = features,
        is_static_linking_mode = True,
    )
    flags = cc_common.get_memory_inefficient_command_line(
        feature_configuration = features,
        action_name = ACTION_NAMES.cpp_link_executable,
        variables = variables,
    )
    return features, flags

def _gcc_link_flags_impl(ctx):
    _, flags = _link_configuration(ctx, ctx.attr.toolchain[cc_common.CcToolchainInfo])
    output = ctx.actions.declare_file(ctx.label.name + ".flags")
    ctx.actions.write(output, "\n".join(flags) + "\n")
    return [DefaultInfo(files = depset([output]))]

gcc_link_flags = rule(
    implementation = _gcc_link_flags_impl,
    attrs = {"toolchain": attr.label(mandatory = True)},
    fragments = ["cpp"],
)

def _gcc_compile_flags_impl(ctx):
    toolchain = ctx.attr.toolchain[cc_common.CcToolchainInfo]
    features = cc_common.configure_features(ctx = ctx, cc_toolchain = toolchain)
    variables = cc_common.create_compile_variables(
        cc_toolchain = toolchain,
        feature_configuration = features,
    )
    flags = cc_common.get_memory_inefficient_command_line(
        feature_configuration = features,
        action_name = ACTION_NAMES.cpp_compile,
        variables = variables,
    )
    output = ctx.actions.declare_file(ctx.label.name + ".flags")
    ctx.actions.write(output, "\n".join(flags) + "\n")
    return [DefaultInfo(files = depset([output]))]

gcc_compile_flags = rule(
    implementation = _gcc_compile_flags_impl,
    attrs = {"toolchain": attr.label(mandatory = True)},
    fragments = ["cpp"],
)

def _gcc_paths_test_impl(ctx):
    env = analysistest.begin(ctx)
    toolchain = analysistest.target_under_test(env)[cc_common.CcToolchainInfo]
    compiler = ctx.file.compiler.path
    root = compiler.rsplit("/bin/", 1)[0]
    prefix = compiler.rsplit("/bin/", 1)[1][:-len("gcc")]
    sysroot = ctx.file.sysroot.path
    asserts.equals(env, compiler, toolchain.compiler_executable)
    asserts.equals(env, root + "/bin/" + prefix + "ar", toolchain.ar_executable)
    asserts.equals(env, root + "/bin/ld.lld", toolchain.ld_executable)
    for files in [toolchain.all_files, toolchain._linker_files]:
        paths = [file.path for file in files.to_list()]
        asserts.true(env, root + "/bin/ld.lld" in paths, "Missing staged ld.lld")
        asserts.true(env, ctx.file.lld.path in paths, "Missing LLVM lld input")
        asserts.true(env, root + "/bin/" + prefix + "dwp" in paths, "Missing staged dwp")
        asserts.true(env, ctx.file.dwp.path in paths, "Missing LLVM dwp input")
        asserts.false(env, any(["/xbin/" in path for path in paths]), "Unexpected xbin wrapper")
    features, flags = _link_configuration(ctx, toolchain)
    for flag in ["-fuse-ld=lld", "-B" + root + "/bin/", "-Wl,-z,noexecstack"]:
        asserts.true(env, flag in flags, "Missing linker flag: " + flag)
    asserts.true(env, cc_common.is_enabled(feature_configuration = features, feature_name = "supports_start_end_lib"))
    compile_features = cc_common.configure_features(ctx = ctx, cc_toolchain = toolchain)
    compile_flags = cc_common.get_memory_inefficient_command_line(
        feature_configuration = compile_features,
        action_name = ACTION_NAMES.cpp_compile,
        variables = cc_common.create_compile_variables(cc_toolchain = toolchain, feature_configuration = compile_features),
    )
    for flag in [
        "-U_FORTIFY_SOURCE",
        "-fstack-protector",
        "-fno-omit-frame-pointer",
        "-no-canonical-prefixes",
        "-fno-canonical-system-headers",
        "-D__DATE__=\"redacted\"",
        "-D__TIMESTAMP__=\"redacted\"",
        "-D__TIME__=\"redacted\"",
    ]:
        asserts.true(env, flag in compile_flags, "Missing compile flag: " + flag)
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
        "dwp": attr.label(allow_single_file = True),
        "lld": attr.label(allow_single_file = True),
        "sysroot": attr.label(allow_single_file = True),
    },
    fragments = ["cpp"],
)

def _gcc_runtime_test_impl(ctx):
    env = analysistest.begin(ctx)
    info = analysistest.target_under_test(env)[CcInfo]
    cc = info.compilation_context
    root = ctx.file.compiler.path.rsplit("/bin/", 1)[0]
    prefix = root + ("/aarch64-linux" if ctx.attr.arch == "aarch64" else "")
    include = prefix + "/include/c++/" + ctx.attr.version

    # cc_library(includes = ...) is reported as includes, system_includes or,
    # for external repositories on newer Bazel, external_includes. Check the union.
    all_includes = (
        cc.includes.to_list() +
        cc.system_includes.to_list() +
        cc.quote_includes.to_list() +
        (cc.external_includes.to_list() if hasattr(cc, "external_includes") else [])
    )
    for directory in [include, include + "/" + ctx.attr.arch + "-linux", include + "/backward"]:
        asserts.true(env, directory in all_includes, "Missing repository-rooted C++ include: " + directory)
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

def _gcc_opt_flags_test_impl(ctx):
    env = analysistest.begin(ctx)
    toolchain = analysistest.target_under_test(env)[cc_common.CcToolchainInfo]

    # cc rules request the compilation mode's feature; custom rules must do so explicitly.
    features = cc_common.configure_features(
        ctx = ctx,
        cc_toolchain = toolchain,
        requested_features = ctx.features + ["opt"],
    )
    compile_flags = cc_common.get_memory_inefficient_command_line(
        feature_configuration = features,
        action_name = ACTION_NAMES.cpp_compile,
        variables = cc_common.create_compile_variables(cc_toolchain = toolchain, feature_configuration = features),
    )
    for flag in ["-g0", "-O2", "-D_FORTIFY_SOURCE=1", "-DNDEBUG", "-ffunction-sections", "-fdata-sections"]:
        asserts.true(env, flag in compile_flags, "Missing opt compile flag: " + flag)
    link_flags = cc_common.get_memory_inefficient_command_line(
        feature_configuration = features,
        action_name = ACTION_NAMES.cpp_link_executable,
        variables = cc_common.create_link_variables(
            cc_toolchain = toolchain,
            feature_configuration = features,
            is_static_linking_mode = True,
        ),
    )
    asserts.true(env, "-Wl,--gc-sections" in link_flags, "Missing opt link flag: -Wl,--gc-sections")
    return analysistest.end(env)

gcc_opt_flags_test = analysistest.make(
    _gcc_opt_flags_test_impl,
    fragments = ["cpp"],
)
