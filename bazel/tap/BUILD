load("@bazel_skylib//:bzl_library.bzl", "bzl_library")
load("@rules_python//python:defs.bzl", "py_library")

exports_files(["defs.bzl"])

bzl_library(
    name = "tap_bzl",
    srcs = ["defs.bzl"],
    visibility = ["//visibility:public"],
    deps = [
        "@bazel_skylib//rules:write_file",
        "@rules_python//python:defs_bzl",
    ],
)

py_library(
    name = "tap2pcap",
    srcs = ["tap2pcap.py"],
    imports = ["."],
    visibility = ["//visibility:public"],
)
