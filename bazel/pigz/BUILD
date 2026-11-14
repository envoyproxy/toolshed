load("@bazel_skylib//:bzl_library.bzl", "bzl_library")
load(":toolchain.bzl", "pigz_unavailable", "resolved_pigz")

exports_files([
    "README.md",
    "defs.bzl",
    "repositories.bzl",
    "toolchain.bzl",
])

bzl_library(
    name = "pigz_bzl",
    srcs = [
        "defs.bzl",
        "repositories.bzl",
        "toolchain.bzl",
        "//pigz/private:pigz_prebuilt.bzl",
    ],
    visibility = ["//visibility:private"],
)

# Toolchain type for hermetic pigz implementations.
toolchain_type(
    name = "toolchain_type",
    visibility = ["//visibility:public"],
)

# Registered last: resolved where there is no other pigz toolchain, it fails with a message.
pigz_unavailable(
    name = "unavailable_impl",
)

toolchain(
    name = "unavailable_toolchain",
    toolchain = ":unavailable_impl",
    toolchain_type = ":toolchain_type",
)

# `pigz` for the platform it runs on: use it as a tool, eg
# `pkg_tar(compressor = "@envoy_toolshed//pigz", extension = "tar.gz")`.
resolved_pigz(
    name = "pigz",
    # Not built with `//...`: there is no pigz where there is no prebuilt for the platform (macOS, or
    # anywhere until the release preparation sets the hashes). Built when used as a tool.
    tags = ["manual"],
    visibility = ["//visibility:public"],
)
