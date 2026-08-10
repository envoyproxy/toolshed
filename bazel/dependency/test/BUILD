load("@bazel_skylib//:bzl_library.bzl", "bzl_library")
load("@rules_shell//shell:sh_test.bzl", "sh_test")
load("//dependency:reachability.bzl", "dependency_reachability")
load(":reachability_apparent_name_test.bzl", "apparent_name_test")

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

sh_test(
    name = "reachability_test",
    size = "small",
    srcs = ["reachability_test.sh"],
    data = [
        ":reachability",
        "@jq_toolchains//:resolved_toolchain",
    ],
    env = {
        "JQ_BIN": "$(JQ_BIN)",
    },
    toolchains = ["@jq_toolchains//:resolved_toolchain"],
)

bzl_library(
    name = "reachability_apparent_name_test_lib",
    srcs = ["reachability_apparent_name_test.bzl"],
    deps = [
        "@bazel_skylib//lib:unittest",
    ],
)

apparent_name_test(
    name = "apparent_name_test",
)
