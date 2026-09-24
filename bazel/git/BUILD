load("@aspect_bazel_lib//lib:copy_file.bzl", "copy_file")
load("@bazel_skylib//:bzl_library.bzl", "bzl_library")
load("//:versions.bzl", "VERSIONS")

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

[
    copy_file(
        name = "git_%s_tar" % platform.replace("-", "_"),
        src = "@envoy_toolshed_git_source//:git_%s" % platform.replace("-", "_"),
        out = "git-%s-%s.tar.zst" % (VERSIONS["git"], platform),
        tags = ["manual"],
        visibility = ["//git/test:__pkg__"],
    )
    for platform in [
        "linux-aarch64",
        "linux-x86_64",
    ]
]

filegroup(
    name = "git_packages",
    srcs = [
        ":git_linux_aarch64_tar",
        ":git_linux_x86_64_tar",
    ],
    tags = ["manual"],
    target_compatible_with = ["@platforms//os:linux"],
    visibility = ["//visibility:public"],
)
