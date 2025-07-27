"""Rule for depending on the current glint toolchain."""

def _current_glint_toolchain_impl(ctx):
    """Implementation for current_glint_toolchain rule."""
    toolchain = ctx.toolchains["//toolchains/glint:glint_toolchain_type"]
    if not toolchain:
        fail("No glint toolchain found. Did you register the toolchain?")

    info = toolchain.glint_info
    files = []
    if hasattr(info, "glint_file") and info.glint_file:
        files.append(info.glint_file)

    return [
        DefaultInfo(files = depset(files)),
    ]

current_glint_toolchain = rule(
    implementation = _current_glint_toolchain_impl,
    toolchains = ["//toolchains/glint:glint_toolchain_type"],
)
