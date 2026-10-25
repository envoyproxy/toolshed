load("@bazel_skylib//:bzl_library.bzl", "bzl_library")
load("@bazel_skylib//lib:selects.bzl", "selects")
load(":wee8_prebuilt.bzl", "wee8_prebuilt_repo_name")
load(":wee8_prebuilt_test.bzl", "wee8_prebuilt_helpers_test")

licenses(["notice"])

config_setting(
    name = "linux_x86_64_platform",
    constraint_values = [
        "@platforms//os:linux",
        "@platforms//cpu:x86_64",
    ],
)

config_setting(
    name = "linux_aarch64_platform",
    constraint_values = [
        "@platforms//os:linux",
        "@platforms//cpu:aarch64",
    ],
)

config_setting(
    name = "clang_build",
    flag_values = {"@bazel_tools//tools/cpp:compiler": "clang"},
)

selects.config_setting_group(
    name = "linux_x86_64",
    match_all = [
        ":linux_x86_64_platform",
        ":clang_build",
    ],
)

selects.config_setting_group(
    name = "linux_aarch64",
    match_all = [
        ":linux_aarch64_platform",
        ":clang_build",
    ],
)

selects.config_setting_group(
    name = "linux_x86_64_gcc",
    match_all = [
        ":linux_x86_64_platform",
        "//compile:gcc_build",
    ],
)

selects.config_setting_group(
    name = "linux_aarch64_gcc",
    match_all = [
        ":linux_aarch64_platform",
        "//compile:gcc_build",
    ],
)

# Falls back to @wee8_source//:wee8, which consumers configure with
# `wee8_prebuilt_extension.setup(source = "@v8//:wee8")`. Without that the
# fallback is an incompatible stub.
alias(
    name = "wee8",
    actual = select({
        ":linux_x86_64_gcc": "@%s//:wee8" % wee8_prebuilt_repo_name("x86_64", "libstdcxx"),
        ":linux_x86_64": "@%s//:wee8" % wee8_prebuilt_repo_name("x86_64"),
        ":linux_aarch64_gcc": "@%s//:wee8" % wee8_prebuilt_repo_name("aarch64", "libstdcxx"),
        ":linux_aarch64": "@%s//:wee8" % wee8_prebuilt_repo_name("aarch64"),
        "//conditions:default": "@wee8_source//:wee8",
    }),
    tags = ["manual"],
    visibility = ["//visibility:public"],
)

alias(
    name = "wee8_packages",
    actual = "//v8/package:wee8_packages",
    tags = ["manual"],
    visibility = ["//visibility:public"],
)

bzl_library(
    name = "wee8_prebuilt_test_lib",
    srcs = ["wee8_prebuilt_test.bzl"],
    tags = ["manual"],
    deps = [
        "@bazel_skylib//lib:unittest",
    ],
)

wee8_prebuilt_helpers_test(
    name = "wee8_prebuilt_helpers_test",
)
