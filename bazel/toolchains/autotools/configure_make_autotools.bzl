"""Wrapper macro for configure_make with autotools support."""

load("@rules_foreign_cc//foreign_cc:defs.bzl", "configure_make")

def configure_make_with_autotools(
        name,
        build_data = None,
        env = None,
        configure_prefix = None,
        **kwargs):
    """Configure and build using autotools with hermetic toolchain.

    This macro wraps configure_make to automatically include the autotools
    toolchain (m4, autoconf, automake, libtool).

    Args:
        name: Target name
        build_data: Additional tools to include (will be merged with autotools)
        env: Environment variables (will be merged with autotools env)
        configure_prefix: Commands to run before configure (will be extended with PATH setup)
        **kwargs: All other arguments passed to configure_make
    """

    # Select autotools based on platform
    autotools_deps = select({
        "@platforms//cpu:x86_64": ["@autotools_x86_64//:all"],
        "@platforms//cpu:aarch64": ["@autotools_aarch64//:all"],
    })

    # Merge build_data
    if build_data:
        all_tools = autotools_deps + build_data
    else:
        all_tools = autotools_deps

    # Set up environment variables
    autotools_env = {
        "M4": "$EXT_BUILD_DEPS$/bin/m4",
        "AUTOCONF": "$EXT_BUILD_DEPS$/bin/autoconf",
        "AUTOHEADER": "$EXT_BUILD_DEPS$/bin/autoheader",
        "AUTORECONF": "$EXT_BUILD_DEPS$/bin/autoreconf",
        "AUTOMAKE": "$EXT_BUILD_DEPS$/bin/automake",
        "ACLOCAL": "$EXT_BUILD_DEPS$/bin/aclocal",
        "LIBTOOLIZE": "$EXT_BUILD_DEPS$/bin/libtoolize",
        "LIBTOOL": "$EXT_BUILD_DEPS$/bin/libtool",
        "ACLOCAL_PATH": "$EXT_BUILD_DEPS$/share/aclocal:$EXT_BUILD_DEPS$/share/aclocal-1.17",
        "AUTOM4TE": "$EXT_BUILD_DEPS$/bin/autom4te",
        "pkgauxdir": "$EXT_BUILD_DEPS$/share/libtool/build-aux",
        "pkgdatadir": "$EXT_BUILD_DEPS$/share/libtool",
    }

    if env:
        autotools_env.update(env)

    # Set up configure prefix with PATH
    autotools_prefix = "export PATH=$EXT_BUILD_DEPS$/bin:$PATH && "
    if configure_prefix:
        autotools_prefix = autotools_prefix + configure_prefix

    configure_make(
        name = name,
        build_data = all_tools,
        env = autotools_env,
        configure_prefix = autotools_prefix,
        **kwargs
    )
