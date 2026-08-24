load("@bazel_skylib//:bzl_library.bzl", "bzl_library")
load("@bazel_skylib//rules:common_settings.bzl", "string_flag")
load("@rules_shell//shell:sh_test.bzl", "sh_test")
load("//dependency:reachability.bzl", "dependency_reachability")
load(":reachability_apparent_name_test.bzl", "apparent_name_test")
load(":reachability_config_validation_test.bzl", "reachability_config_validation_test")
load(":reachability_test_rules.bzl", "dependency_reachability_with_mode")

sh_test(
    name = "updater_test",
    size = "small",
    srcs = ["updater_test.sh"],
    data = [
        "//dependency:bazel-update.sh",
        "testdata/dependency_versions.json",
        "testdata/versions.bzl",
        "@jq_toolchains//:resolved_toolchain",
    ],
    env = {
        "JQ_BIN": "$(JQ_BIN)",
    },
    toolchains = ["@jq_toolchains//:resolved_toolchain"],
)

filegroup(
    name = "external_consumer",
    srcs = ["@bazel_skylib//lib:paths"],
)

filegroup(
    name = "core_root",
    srcs = [":external_consumer"],
)

filegroup(
    name = "test_root",
    testonly = True,
    srcs = [
        ":external_consumer",
        "@bazel_skylib//lib:sets",
    ],
)

dependency_reachability(
    name = "reachability",
    testonly = True,
    roots = [
        ":core_root",
        ":test_root",
    ],
)

string_flag(
    name = "reachability_mode",
    build_setting_default = "default",
    values = ["default", "extra"],
)

config_setting(
    name = "reachability_mode_extra",
    flag_values = {":reachability_mode": "extra"},
)

filegroup(
    name = "variant_external_consumer",
    srcs = [
        "@bazel_skylib//lib:paths",
    ] + select({
        ":reachability_mode_extra": ["@jq_toolchains//:resolved_toolchain"],
        "//conditions:default": [],
    }),
)

filegroup(
    name = "variant_core_root",
    srcs = [":variant_external_consumer"],
)

filegroup(
    name = "variant_test_root",
    testonly = True,
    srcs = [
        ":variant_external_consumer",
        "@bazel_skylib//lib:sets",
    ],
)

dependency_reachability_with_mode(
    name = "reachability_multiconfig",
    testonly = True,
    roots = [
        ":variant_core_root",
        ":variant_test_root",
    ],
    configs = {
        "default": [],
        "extra": ["//dependency/test:reachability_mode=extra"],
    },
)

dependency_reachability(
    name = "reachability_invalid_config_flag",
    testonly = True,
    roots = [
        ":core_root",
    ],
    configs = {
        "invalid": {"//dependency/test:reachability_mode": "extra"},
    },
)

sh_test(
    name = "reachability_test",
    size = "small",
    srcs = ["reachability_test.sh"],
    data = [
        ":reachability",
        ":reachability_multiconfig",
        "@jq_toolchains//:resolved_toolchain",
    ],
    env = {
        "JQ_BIN": "$(JQ_BIN)",
    },
    toolchains = ["@jq_toolchains//:resolved_toolchain"],
)

bzl_library(
    name = "reachability_apparent_name_test_lib",
    srcs = [
        "reachability_apparent_name_test.bzl",
        "reachability_config_validation_test.bzl",
        "reachability_test_rules.bzl",
    ],
    deps = [
        "@bazel_skylib//lib:unittest",
    ],
)

apparent_name_test(
    name = "apparent_name_test",
)

reachability_config_validation_test(
    name = "reachability_config_validation_test",
)
