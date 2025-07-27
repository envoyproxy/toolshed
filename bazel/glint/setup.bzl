"""Full glint setup for external repositories."""

load("//glint:archives.bzl", "setup_glint_archives")

def setup_glint(register_toolchains = True):
    """Set up glint for use in external repositories.

    This function:
    1. Downloads the prebuilt glint binaries for supported architectures
    2. Registers the toolchains

    For unsupported architectures, it will fall back to building from source.

    Args:
        register_toolchains: Whether to register the glint toolchains (default: True)
    """
    # Set up the archives for prebuilt binaries
    setup_glint_archives()

    # Register toolchains
    if register_toolchains:
        native.register_toolchains(
            "@envoy_toolshed//toolchains/glint:hermetic_glint_toolchain",
            "@envoy_toolshed//toolchains/glint:preinstalled_glint_toolchain",
        )
