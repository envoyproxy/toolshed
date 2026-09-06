load("@bazel_skylib//:bzl_library.bzl", "bzl_library")
load(":defs.bzl", "pgp_audit_binary")

exports_files([
    "audit.jq",
    "audit.sh.tpl",
    "audit_result_test.sh.tpl",
    "defs.bzl",
    "lib.jq",
])

pgp_audit_binary(
    name = "audit",
    visibility = ["//visibility:public"],
)

bzl_library(
    name = "audit_bzl",
    srcs = ["defs.bzl"],
    visibility = ["//pgp:__pkg__"],
    deps = [
        "@bazel_skylib//lib:shell",
    ],
)
