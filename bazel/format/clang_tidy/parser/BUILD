load("@aspect_bazel_lib//lib:jq.bzl", "jq")
load("@rules_shell//shell:sh_binary.bzl", "sh_binary")

exports_files([
    "parse_clang_tidy.sh",
])

sh_binary(
    name = "parse_clang_tidy",
    srcs = ["parse_clang_tidy.sh"],
    data = [
        "@envoy_toolshed_jq//:modules",
        "@envoy_toolshed_jq//:modules_root.marker",
        "@jq_toolchains//:resolved_toolchain",
    ],
    deps = ["@bazel_tools//tools/bash/runfiles"],
    env = {
        "JQ_BIN": "$(rlocationpath @jq_toolchains//:resolved_toolchain)",
        "JQ_MODULES_ROOT_MARKER": "$(rlocationpath @envoy_toolshed_jq//:modules_root.marker)",
    },
    visibility = ["//visibility:public"],
)
