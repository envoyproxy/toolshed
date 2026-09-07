"""Build and package the registry sq source target for Linux toolchains."""

load("@aspect_bazel_lib//lib:tar.bzl", "mtree_mutate", "mtree_spec", "tar")
load("@rules_pkg//pkg:providers.bzl", "PackageFilesInfo")
load("//:versions.bzl", "VERSIONS")

_PLATFORMS = {
    "Linux-X64": "@toolchains_llvm//platforms:linux-x86_64",
    "Linux-ARM64": "@toolchains_llvm//platforms:linux-aarch64",
}

def _sq_transition_impl(settings, attr):
    return {"//command_line_option:platforms": [_PLATFORMS[attr.platform]]}

_sq_transition = transition(
    implementation = _sq_transition_impl,
    inputs = [],
    outputs = ["//command_line_option:platforms"],
)

def _sq_binary_impl(ctx):
    package_dir = "sq-%s-%s" % (VERSIONS["sq"], ctx.attr.platform)
    out = ctx.actions.declare_file(package_dir + "/bin/sq")
    sq = ctx.attr.sq[0][DefaultInfo].files.to_list()[0]
    ctx.actions.run_shell(
        inputs = [sq],
        tools = [ctx.executable.stripper],
        outputs = [out],
        command = "mkdir -p $(dirname \"$3\") && \"$2\" -o \"$3\" \"$1\"",
        arguments = [sq.path, ctx.executable.stripper.path, out.path],
        mnemonic = "SqStrip",
        progress_message = "Stripping sq for " + ctx.attr.platform,
    )
    return [
        DefaultInfo(files = depset([out])),
        PackageFilesInfo(dest_src_map = {"bin/sq": out}, attributes = {}),
    ]

sq_binary = rule(
    implementation = _sq_binary_impl,
    attrs = {
        "sq": attr.label(
            mandatory = True,
            executable = True,
            cfg = _sq_transition,
        ),
        "platform": attr.string(mandatory = True, values = _PLATFORMS.keys()),
        "stripper": attr.label(
            mandatory = True,
            executable = True,
            cfg = "exec",
            allow_single_file = True,
        ),
        "_allowlist_function_transition": attr.label(
            default = "@bazel_tools//tools/allowlists/function_transition_allowlist",
        ),
    },
)

def sq_package(name, platform, stripper):
    package_dir = "sq-%s-%s" % (VERSIONS["sq"], platform)
    binary = name + "_binary"
    build = name + "_build"
    native.genrule(
        name = build,
        outs = [package_dir + "/BUILD.bazel"],
        cmd = """cat >"$@" <<'EOF'
exports_files(["bin/sq"])
filegroup(name = "sq", srcs = ["bin/sq"], visibility = ["//visibility:public"])
EOF""",
        tags = ["manual"],
    )
    sq_binary(
        name = binary,
        platform = platform,
        sq = "@sq//:sq_from_source",
        stripper = stripper,
        tags = ["manual"],
    )
    mtree_spec(
        name = name + "_mtree_src",
        srcs = [":" + binary, ":" + build],
        tags = ["manual"],
    )
    mtree_mutate(
        name = name + "_mtree",
        mtree = ":" + name + "_mtree_src",
        package_dir = package_dir,
        strip_prefix = "pgp/" + package_dir,
        tags = ["manual"],
    )
    tar(
        name = name,
        args = ["--options=zstd:compression-level=19,zstd:threads=4"],
        compress = "zstd",
        exec_properties = {"Pool": "linux_x64_xlarge"},
        mtree = ":" + name + "_mtree",
        out = package_dir + ".tar.zst",
        srcs = [":" + binary, ":" + build],
        tags = ["manual"],
    )
