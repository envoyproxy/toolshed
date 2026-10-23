load("@bazel_skylib//:bzl_library.bzl", "bzl_library")
load(":repository_utils_alias_name_test.bzl", "alias_name_test")

exports_files([
    "extensions.bzl",
    "utils.bzl",
])

bzl_library(
    name = "repository_extensions_bzl",
    srcs = ["extensions.bzl"],
    deps = [":repository_utils_bzl"],
)

bzl_library(
    name = "repository_utils_bzl",
    srcs = ["utils.bzl"],
)

bzl_library(
    name = "repository_utils_alias_name_test_lib",
    srcs = ["repository_utils_alias_name_test.bzl"],
    deps = [
        ":repository_utils_bzl",
        "@bazel_skylib//lib:unittest",
    ],
)

alias(
    name = "arch_alias_extension_smoke",
    actual = "@toolshed_arch_alias_smoke//:toolshed_arch_alias_smoke",
)

alias_name_test(
    name = "alias_name_test",
)
