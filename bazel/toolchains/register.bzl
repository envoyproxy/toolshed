
def toolshed_toolchains():
    native.register_toolchains(
        "@envoy_toolshed//toolchains/autotools:hermetic_autotools_toolchain",
        "@envoy_toolshed//toolchains/autotools:preinstalled_autotools_toolchain",
        "@envoy_toolshed//toolchains/glint:hermetic_glint_toolchain",
        "@envoy_toolshed//toolchains/glint:preinstalled_glint_toolchain",
    )
