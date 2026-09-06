load("@bazel_skylib//:bzl_library.bzl", "bzl_library")
load("@rules_cc//cc:defs.bzl", "cc_binary")

licenses(["notice"])  # Apache 2

exports_files(["certs.bzl"])

# Hermetic, in-process test certificate generator.
#
# Links BoringSSL directly so that the fixtures it emits are reproducible and
# do not depend on any TLS provider configuration in the consuming workspace.
cc_binary(
    name = "gen",
    srcs = ["gen.cc"],
    visibility = ["//visibility:public"],
    deps = ["@boringssl//:crypto"],
)

bzl_library(
    name = "certs_bzl",
    srcs = ["certs.bzl"],
    visibility = ["//visibility:public"],
)
