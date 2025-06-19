load(":autotools_toolchain.bzl", "autotools_toolchain")
load(":current_toolchain.bzl", "current_autotools_toolchain")

package(default_visibility = ["//visibility:public"])

# Toolchain type for autotools
toolchain_type(
    name = "autotools_toolchain_type",
)

# Preinstalled autotools (fallback)
autotools_toolchain(
    name = "preinstalled_autotools",
    m4_path = "m4",
    autoconf_path = "autoconf",
    automake_path = "automake",
    libtool_path = "libtool",
)

toolchain(
    name = "preinstalled_autotools_toolchain",
    toolchain = ":preinstalled_autotools",
    toolchain_type = ":autotools_toolchain_type",
)

# Hermetic autotools toolchain
autotools_toolchain(
    name = "hermetic_autotools",
    m4 = select({
        "@platforms//cpu:x86_64": "@autotools_x86_64//:m4",
        "@platforms//cpu:aarch64": "@autotools_aarch64//:m4",
    }),
    autoconf = select({
        "@platforms//cpu:x86_64": "@autotools_x86_64//:autoconf",
        "@platforms//cpu:aarch64": "@autotools_aarch64//:autoconf",
    }),
    autoheader = select({
        "@platforms//cpu:x86_64": "@autotools_x86_64//:autoheader",
        "@platforms//cpu:aarch64": "@autotools_aarch64//:autoheader",
    }),
    autoreconf = select({
        "@platforms//cpu:x86_64": "@autotools_x86_64//:autoreconf",
        "@platforms//cpu:aarch64": "@autotools_aarch64//:autoreconf",
    }),
    automake = select({
        "@platforms//cpu:x86_64": "@autotools_x86_64//:automake",
        "@platforms//cpu:aarch64": "@autotools_aarch64//:automake",
    }),
    aclocal = select({
        "@platforms//cpu:x86_64": "@autotools_x86_64//:aclocal",
        "@platforms//cpu:aarch64": "@autotools_aarch64//:aclocal",
    }),
    libtool = select({
        "@platforms//cpu:x86_64": "@autotools_x86_64//:libtool",
        "@platforms//cpu:aarch64": "@autotools_aarch64//:libtool",
    }),
    libtoolize = select({
        "@platforms//cpu:x86_64": "@autotools_x86_64//:libtoolize",
        "@platforms//cpu:aarch64": "@autotools_aarch64//:libtoolize",
    }),
    data = select({
        "@platforms//cpu:x86_64": ["@autotools_x86_64//:all"],
        "@platforms//cpu:aarch64": ["@autotools_aarch64//:all"],
    }),
    perl_runtime = select({
        "@platforms//cpu:x86_64": ["@perl_linux_amd64//:runtime"],
        "@platforms//cpu:aarch64": ["@perl_linux_arm64//:runtime"],
    }),
)

toolchain(
    name = "hermetic_autotools_toolchain",
    toolchain = ":hermetic_autotools",
    toolchain_type = ":autotools_toolchain_type",
)

# Current toolchain for use in toolchains attribute
current_autotools_toolchain(
    name = "current_autotools_toolchain",
)
