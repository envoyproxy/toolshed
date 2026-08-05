load("@bazel_skylib//:bzl_library.bzl", "bzl_library")
load(":repository_utils_alias_name_test.bzl", "alias_name_test")

exports_files(["utils.bzl"])

bzl_library(
    name = "repository_utils_alias_name_test_lib",
    srcs = ["repository_utils_alias_name_test.bzl"],
    deps = [
        "@bazel_skylib//lib:unittest",
    ],
)

alias_name_test(
    name = "alias_name_test",
)
