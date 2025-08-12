"""Glint toolchain definition."""

GlintInfo = provider(
    doc = "Information about a glint installation",
    fields = {
        "glint": "Path to glint binary",
        "glint_file": "File reference to glint binary",
    },
)

def _glint_toolchain_impl(ctx):
    """Implementation for glint toolchain rule."""

    # Get file reference if provided
    glint_file = ctx.file.glint if hasattr(ctx.file, "glint") else None

    # Get path - either from file reference or from path attribute
    if glint_file:
        glint_path = glint_file.path
    else:
        glint_path = ctx.attr.glint_path or "glint"

    # Build the info provider
    info_fields = {
        "glint": glint_path,
    }
    if glint_file:
        info_fields["glint_file"] = glint_file

    return [
        platform_common.ToolchainInfo(
            glint_info = GlintInfo(**info_fields),
        ),
    ]

glint_toolchain = rule(
    implementation = _glint_toolchain_impl,
    attrs = {
        "glint": attr.label(
            doc = "Glint executable file",
            allow_single_file = True,
            executable = True,
            cfg = "exec",
        ),
        "glint_path": attr.string(
            doc = "Path to glint executable (for preinstalled toolchain)",
        ),
    },
    provides = [platform_common.ToolchainInfo],
)

def get_glint_data(ctx):
    """Get glint data from the toolchain.

    Args:
        ctx: The rule context

    Returns:
        A struct containing:
        - glint: Path to glint binary
        - glint_file: File reference to glint binary (if available)
    """
    toolchain = ctx.toolchains["//toolchains/glint:glint_toolchain_type"]
    if not toolchain:
        fail("No glint toolchain found. Did you register the toolchain?")

    info = toolchain.glint_info
    result = {"glint": info.glint}
    if hasattr(info, "glint_file") and info.glint_file:
        result["glint_file"] = info.glint_file
    return struct(**result)
