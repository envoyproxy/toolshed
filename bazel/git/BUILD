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
        "//git/private:git_package.bzl",
        "//git/private:git_prebuilt.bzl",
        "//git/private:git_source.bzl",
        "//git/private:transitions.bzl",
    ],
    visibility = ["//visibility:private"],
    deps = ["//private:extension_utils_bzl"],
)

# Toolchain type for hermetic git implementations.
toolchain_type(
    name = "toolchain_type",
    visibility = ["//visibility:public"],
)

alias(
    name = "source_toolchain",
    actual = "//git/dev:source_toolchain",
    visibility = ["//visibility:public"],
)

alias(
    name = "git_linux_x86_64",
    actual = "//git/dev:git_linux_x86_64",
    visibility = ["//visibility:public"],
)

alias(
    name = "git_linux_aarch64",
    actual = "//git/dev:git_linux_aarch64",
    visibility = ["//visibility:public"],
)

alias(
    name = "git_packages",
    actual = "//git/dev:git_packages",
    visibility = ["//visibility:public"],
)
