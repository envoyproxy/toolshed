load("@bazel_skylib//:bzl_library.bzl", "bzl_library")
load("//git/private:git_package.bzl", "git_package")

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

# Packaging targets stay in the public package so toolshed CI always emits the
# published tarballs at stable bazel-bin paths. They remain `manual`, so only
# toolshed's own explicit CI builds analyze them with the dev-only source deps.
git_package(
    name = "git_linux_x86_64",
    platform = "linux-x86_64",
    stripper = "//compile:llvm_minimal_host_llvm_strip",
    visibility = ["//visibility:public"],
)

git_package(
    name = "git_linux_aarch64",
    platform = "linux-aarch64",
    stripper = "//compile:llvm_minimal_host_llvm_strip",
    visibility = ["//visibility:public"],
)

filegroup(
    name = "git_packages",
    srcs = [
        ":git_linux_aarch64",
        ":git_linux_x86_64",
    ],
    tags = ["manual"],
    target_compatible_with = ["@platforms//os:linux"],
    visibility = ["//visibility:public"],
)
