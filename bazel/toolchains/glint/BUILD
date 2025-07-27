load(":glint_toolchain.bzl", "glint_toolchain")
load(":current_toolchain.bzl", "current_glint_toolchain")

package(default_visibility = ["//visibility:public"])

# Toolchain type for glint
toolchain_type(
    name = "glint_toolchain_type",
)

# Preinstalled glint (fallback)
glint_toolchain(
    name = "preinstalled_glint",
    glint_path = "glint",
)

toolchain(
    name = "preinstalled_glint_toolchain",
    toolchain = ":preinstalled_glint",
    toolchain_type = ":glint_toolchain_type",
)

# Hermetic glint toolchain - uses prebuilt binaries or builds from source
glint_toolchain(
    name = "hermetic_glint",
    glint = select({
        "@platforms//cpu:x86_64": "@glint_amd64//:glint",
        "@platforms//cpu:aarch64": "@glint_arm64//:glint",
        # Fall back to building from source for other architectures
        "//conditions:default": "//rust/glint:glint_binary",
    }),
)

toolchain(
    name = "hermetic_glint_toolchain",
    toolchain = ":hermetic_glint",
    toolchain_type = ":glint_toolchain_type",
)

# Current toolchain for use in toolchains attribute
current_glint_toolchain(
    name = "current_glint_toolchain",
)
