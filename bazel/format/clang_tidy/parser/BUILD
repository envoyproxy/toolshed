load("@aspect_bazel_lib//lib:jq.bzl", "jq")
load("@rules_shell//shell:sh_binary.bzl", "sh_binary")

exports_files([
    "parse_clang_tidy.sh",
])

sh_binary(
    name = "parse_clang_tidy",
    srcs = ["parse_clang_tidy.sh"],
    data = ["@envoy_toolshed_jq//:jq"],
    deps = ["@bazel_tools//tools/bash/runfiles"],
    env = {"JQ_BIN": "$(rlocationpath @envoy_toolshed_jq//:jq)"},
    visibility = ["//visibility:public"],
)
