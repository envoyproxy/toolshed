# Export toolchain types and utilities
exports_files([
    "BUILD",
    "utils.bzl",
])

load("//toolchains:utils.bzl", "current_protoc_toolchain")

current_protoc_toolchain(
    name = "current_protoc",
    visibility = ["//visibility:public"],
)
