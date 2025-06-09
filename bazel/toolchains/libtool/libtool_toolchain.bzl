"""Libtool toolchain implementation."""

LibtoolInfo = provider(
    doc = "Information about a libtool installation",
    fields = {
        "libtoolize": "Path to libtoolize binary",
        "libtool": "Path to libtool binary",
        "env": "Environment variables to set",
        "data": "Additional data dependencies",
    },
)

def _libtool_toolchain_impl(ctx):
    return [
        platform_common.ToolchainInfo(
            libtool_info = LibtoolInfo(
                libtoolize = ctx.attr.libtoolize,
                libtool = ctx.attr.libtool,
                env = ctx.attr.env,
                data = ctx.files.data,
            ),
        ),
    ]

libtool_toolchain = rule(
    implementation = _libtool_toolchain_impl,
    attrs = {
        "libtoolize": attr.string(
            doc = "Path to libtoolize executable",
            mandatory = True,
        ),
        "libtool": attr.string(
            doc = "Path to libtool executable",
            mandatory = True,
        ),
        "env": attr.string_dict(
            doc = "Environment variables to set when using libtool",
            default = {},
        ),
        "data": attr.label_list(
            doc = "Additional files needed by libtool",
            allow_files = True,
        ),
    },
    provides = [platform_common.ToolchainInfo],
)

def get_libtool_data(ctx):
    """Get libtool toolchain data for use in rules.

    Args:
        ctx: The rule context

    Returns:
        struct with libtoolize path, env vars, and data files
    """
    toolchain = ctx.toolchains["//toolchains/libtool:libtool_toolchain_type"]
    if not toolchain:
        fail("No libtool toolchain found")

    info = toolchain.libtool_info
    return struct(
        libtoolize = info.libtoolize,
        libtool = info.libtool,
        env = info.env,
        data = info.data,
    )
