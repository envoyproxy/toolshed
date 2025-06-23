"""Full autotools setup for external repositories."""

load("//autotools:archives.bzl", "setup_autotools_archives")
load("//autotools:autotools_repo.bzl", "setup_autotools_repo")
load("//toolchains:register.bzl", "toolshed_toolchains")

def setup_autotools(register_toolchains = True):
    """Set up autotools for use in external repositories.

    This function:
    1. Downloads the prebuilt autotools archives
    2. Creates the @autotools repository
    3. Registers the toolchains

    Users can then use:
        toolchains = ["@autotools//:current_toolchain"]

    in their configure_make rules.

    Args:
        register_toolchains: Whether to register the autotools toolchains (default: True)
    """
    # Set up the archives
    setup_autotools_archives()

    # Create the @autotools repo
    setup_autotools_repo()

    # Register toolchains
    if register_toolchains:
        native.register_toolchains(
            "@envoy_toolshed//toolchains/autotools:hermetic_autotools_toolchain",
            "@envoy_toolshed//toolchains/autotools:preinstalled_autotools_toolchain",
        )
