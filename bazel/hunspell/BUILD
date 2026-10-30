load("@bazel_skylib//:bzl_library.bzl", "bzl_library")

exports_files([
    "README.md",
    "defs.bzl",
    "extensions.bzl",
    "toolchain.bzl",
])

bzl_library(
    name = "hunspell_bzl",
    srcs = [
        "defs.bzl",
        "extensions.bzl",
        "toolchain.bzl",
        "//hunspell/private:hunspell_prebuilt.bzl",
    ],
    visibility = ["//visibility:private"],
    deps = ["//private:extension_utils_bzl"],
)

# Toolchain type for hermetic hunspell implementations.
toolchain_type(
    name = "toolchain_type",
    visibility = ["//visibility:public"],
)
