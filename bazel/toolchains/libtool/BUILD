load(":libtool_toolchain.bzl", "libtool_toolchain")

package(default_visibility = ["//visibility:public"])

# Toolchain type for libtool
toolchain_type(
    name = "libtool_toolchain_type",
)

# Preinstalled libtool (fallback)
libtool_toolchain(
    name = "preinstalled_libtool",
    libtoolize = "libtoolize",
    libtool = "libtool",
)

toolchain(
    name = "preinstalled_libtool_toolchain",
    toolchain = ":preinstalled_libtool",
    toolchain_type = ":libtool_toolchain_type",
)

# Hermetic libtool toolchain
libtool_toolchain(
    name = "hermetic_libtool",
    libtoolize = "$EXT_BUILD_DEPS$/bin/libtoolize",
    libtool = "$EXT_BUILD_DEPS$/bin/libtool",
    data = ["//compile:libtool_files"],
    env = {
        "ACLOCAL_PATH": "$EXT_BUILD_DEPS$/share/aclocal",
    },
)

toolchain(
    name = "hermetic_libtool_toolchain",
    toolchain = ":hermetic_libtool",
    toolchain_type = ":libtool_toolchain_type",
)
