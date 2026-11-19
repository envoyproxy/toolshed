"""Expose a C++ toolchain's default command lines, to drive its compiler from a test."""

load("@rules_cc//cc:action_names.bzl", "ACTION_NAMES")
load("@rules_cc//cc/common:cc_common.bzl", "cc_common")

def _gcc_link_flags_impl(ctx):
    toolchain = ctx.attr.toolchain[cc_common.CcToolchainInfo]
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
