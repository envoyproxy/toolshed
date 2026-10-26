load("@bazel_skylib//:bzl_library.bzl", "bzl_library")
load("@cve_pip3//:requirements.bzl", "requirement")
load("@rules_python//python:defs.bzl", "py_binary", "py_test")

package(default_visibility = ["//visibility:public"])

exports_files([
    "scan.sh",
    "test.sh",
    "update.sh",
    "requirements.in",
    "requirements.txt",
])

bzl_library(
    name = "macros",
    srcs = ["macros.bzl"],
    deps = [
        "@aspect_bazel_lib//lib:write_source_files",
        "@aspect_bazel_lib//lib:yq",
        "@envoy_toolshed_jq//:defs.bzl",
        "@rules_shell//shell:rules_bzl",
    ],
)

py_binary(
    name = "fetch",
    srcs = ["fetch.py"],
    python_version = "3.12",
    deps = [
        requirement("aiohttp"),
        requirement("aio.run.runner"),
    ],
)

py_test(
    name = "fetch_test",
    srcs = ["fetch_test.py"],
    deps = [":fetch"],
)
