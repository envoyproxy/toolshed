"""Repository rule for consumer-configured sq source toolchains and packages."""

_BUILD_TEMPLATE = """\
load("{defs_bzl_label}", "pgp_toolchain", "sq_signer")
load("{sq_package_bzl_label}", "sq_package")

sq_signer(
    name = "sq_signer",
    sq = "{sq_label}",
    tags = ["manual"],
    visibility = ["//visibility:public"],
)

pgp_toolchain(
    name = "sq_signer_toolchain",
    signer = ":sq_signer",
    tags = ["manual"],
    visibility = ["//visibility:public"],
)

toolchain(
    name = "source_toolchain",
    toolchain = ":sq_signer_toolchain",
    toolchain_type = "{toolchain_type_label}",
    visibility = ["//visibility:public"],
)

sq_package(
    name = "sq_linux_x86_64",
    platform = "Linux-X64",
    sq = "{sq_label}",
    stripper = "{stripper_label}",
    visibility = ["//visibility:public"],
)

sq_package(
    name = "sq_linux_arm64",
    platform = "Linux-ARM64",
    sq = "{sq_label}",
    stripper = "{stripper_label}",
    visibility = ["//visibility:public"],
)

filegroup(
    name = "sq_packages",
    srcs = [
        ":sq_linux_arm64",
        ":sq_linux_x86_64",
    ],
    tags = ["manual"],
    target_compatible_with = ["@platforms//os:linux"],
    visibility = ["//visibility:public"],
)
"""

def render_sq_source_build(
        *,
        defs_bzl_label,
        sq_label,
        sq_package_bzl_label,
        stripper_label,
        toolchain_type_label):
    return _BUILD_TEMPLATE.format(
        defs_bzl_label = defs_bzl_label,
        sq_label = sq_label,
        sq_package_bzl_label = sq_package_bzl_label,
        stripper_label = stripper_label,
        toolchain_type_label = toolchain_type_label,
    )

def _sq_source_hub_impl(ctx):
    ctx.file("BUILD.bazel", render_sq_source_build(
        defs_bzl_label = ctx.attr.defs_bzl_label,
        sq_label = str(ctx.attr.sq),
        sq_package_bzl_label = ctx.attr.sq_package_bzl_label,
        stripper_label = str(ctx.attr.stripper),
        toolchain_type_label = ctx.attr.toolchain_type_label,
    ))
    return ctx.repo_metadata(reproducible = True)

sq_source_hub = repository_rule(
    implementation = _sq_source_hub_impl,
    attrs = {
        "defs_bzl_label": attr.string(mandatory = True),
        "sq": attr.label(mandatory = True),
        "sq_package_bzl_label": attr.string(mandatory = True),
        "stripper": attr.label(mandatory = True),
        "toolchain_type_label": attr.string(mandatory = True),
    },
)
