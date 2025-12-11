"""Current toolchain resolution for autotools."""

def _current_autotools_toolchain_impl(ctx):
    toolchain = ctx.toolchains["//toolchains/autotools:autotools_toolchain_type"]
    if not toolchain:
        fail("No autotools toolchain found")

    info = toolchain.autotools_info

    # Provide all the data files that foreign_cc should copy
    return [
        DefaultInfo(
            files = depset(info.data),
            runfiles = ctx.runfiles(files = info.data),
        ),
    ]

current_autotools_toolchain = rule(
    implementation = _current_autotools_toolchain_impl,
    toolchains = ["//toolchains/autotools:autotools_toolchain_type"],
    incompatible_use_toolchain_transition = True,
)
