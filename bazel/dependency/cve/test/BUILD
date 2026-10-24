load("@bazel_skylib//rules:diff_test.bzl", "diff_test")
load("@rules_shell//shell:sh_binary.bzl", "sh_binary")
load("@rules_shell//shell:sh_test.bzl", "sh_test")
load("//dependency/cve:macros.bzl", "cve_scan")
load(":analysis_test.bzl", "fetch_action_test", "update_analysis_test")

filegroup(
    name = "data",
    srcs = glob(["cve_data/*.json"]),
)

label_flag(
    name = "cve-data",
    build_setting_default = ":data",
)

cve_scan(
    name = "cves",
    config = "cve.yaml",
    cve_data = ":cve-data",
    deps = "deps.json",
)

cve_scan(
    name = "clean",
    config = "clean.yaml",
    cve_data = ":cve-data",
    deps = "deps.json",
)

cve_scan(
    name = "empty",
    config = "cve.yaml",
    cve_data = ":placeholder",
    deps = "deps.json",
)

filegroup(
    name = "placeholder",
    srcs = ["cve.yaml"],
)

diff_test(
    name = "scanned_test",
    file1 = ":cves.scanned",
    file2 = "expected.json",
)

sh_test(
    name = "failure_test",
    srcs = ["failure_test.sh"],
    data = [
        ":cves.scanned",
        ":cves.test",
        ":empty",
        ":empty_data",
        ":empty_deps",
        ":empty_ignored",
        "@envoy_toolshed_jq//:cve/matcher.jq",
        "@envoy_toolshed_jq//:cve/report.jq",
        "@envoy_toolshed_jq//:modules_root.marker",
        "@jq_toolchains//:resolved_toolchain",
    ],
    env = {
        "CVE_TEST": "$(rlocationpath :cves.test)",
        "EMPTY_SCAN": "$(rlocationpath :empty)",
        "CPE_DEPS": "$(rlocationpath :empty_deps)",
        "CVE_FILES": "$(rlocationpath :empty_data)",
        "CVES_IGNORED": "$(rlocationpath :empty_ignored)",
        "JQ_BIN": "$(rlocationpath @jq_toolchains//:resolved_toolchain)",
        "JQ_CVE_MATCHER": "$(rlocationpath @envoy_toolshed_jq//:cve/matcher.jq)",
        "JQ_REPORT": "$(rlocationpath @envoy_toolshed_jq//:cve/report.jq)",
        "SCANNED": "$(rlocationpath :cves.scanned)",
        "TOOLSHED_JQ_ROOT": "$(rlocationpath @envoy_toolshed_jq//:modules_root.marker)",
    },
    deps = ["@bazel_tools//tools/bash/runfiles"],
)

fetch_action_test(
    name = "fetch_action_test",
    target_under_test = ":cves_fetched",
)

update_analysis_test(
    name = "update_analysis_test",
    target_under_test = ":cves.update",
)

test_suite(
    name = "clean_test",
    tests = [":clean.test"],
)

sh_binary(
    name = "fake_fetch",
    srcs = ["fake_fetch.sh"],
)

sh_test(
    name = "update_test",
    srcs = ["update_test.sh"],
    data = [
        "cve_data/2024-01.json",
        ":cves_data",
        ":cves_start_year",
        ":data",
        ":fake_fetch",
        "//dependency/cve:update.sh",
    ],
    env = {
        "CVE_FILES": "$(rlocationpath :cves_data)",
        "FETCHER": "$(rlocationpath :fake_fetch)",
        "FIXTURE": "$(rlocationpath cve_data/2024-01.json)",
        "START_YEAR_PATH": "$(rlocationpath :cves_start_year)",
        "UPDATE_SCRIPT": "$(rlocationpath //dependency/cve:update.sh)",
    },
    deps = ["@bazel_tools//tools/bash/runfiles"],
)
