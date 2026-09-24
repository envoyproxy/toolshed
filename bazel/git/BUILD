load("@bazel_skylib//:bzl_library.bzl", "bzl_library")

exports_files([
    "README.md",
    "defs.bzl",
    "extensions.bzl",
    "source_defs.bzl",
    "toolchain.bzl",
])

bzl_library(
    name = "git_bzl",
    srcs = [
        "defs.bzl",
        "extensions.bzl",
        "source_defs.bzl",
        "toolchain.bzl",
        "//git/private:git_prebuilt.bzl",
        "//git/private:git_source.bzl",
        "//git/private:git_source_hub.bzl",
    ],
    visibility = ["//visibility:private"],
    deps = ["//private:extension_utils_bzl"],
)

# Toolchain type for hermetic git implementations.
toolchain_type(
    name = "toolchain_type",
    visibility = ["//visibility:public"],
)
