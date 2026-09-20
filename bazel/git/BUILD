load("@bazel_skylib//:bzl_library.bzl", "bzl_library")
load("@rules_shell//shell:sh_test.bzl", "sh_test")
load("//git/private:git_package.bzl", "git_package")

exports_files(["README.md"])

bzl_library(
    name = "git_bzl",
    srcs = ["//git/private:git_package.bzl"],
    visibility = ["//visibility:private"],
)

git_package(
    name = "git_linux_x86_64",
    platform = "linux-x86_64",
    stripper = "//compile:llvm_minimal_host_llvm_strip",
    visibility = ["//visibility:public"],
)

git_package(
    name = "git_linux_aarch64",
    platform = "linux-aarch64",
    stripper = "//compile:llvm_minimal_host_llvm_strip",
    visibility = ["//visibility:public"],
)

filegroup(
    name = "git_packages",
    srcs = [":git_linux_x86_64", ":git_linux_aarch64"],
    tags = ["manual"],
    target_compatible_with = ["@platforms//os:linux"],
    visibility = ["//visibility:public"],
)
