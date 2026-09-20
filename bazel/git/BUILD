load("@bazel_skylib//:bzl_library.bzl", "bzl_library")
load("@rules_shell//shell:sh_test.bzl", "sh_test")
load("//:versions.bzl", "VERSIONS")
load("//git/private:git_package.bzl", "git_package")

exports_files(["README.md"])

bzl_library(
    name = "git_bzl",
    srcs = ["//git/private:git_package.bzl"],
    visibility = ["//visibility:private"],
)

git_package(
    name = "git_linux_x86_64",
    platform = "Linux-X64",
    stripper = "//compile:llvm_minimal_host_llvm_strip",
)

git_package(
    name = "git_linux_arm64",
    platform = "Linux-ARM64",
    stripper = "//compile:llvm_minimal_host_llvm_strip",
)

filegroup(
    name = "git_packages",
    srcs = [":git_linux_x86_64", ":git_linux_arm64"],
    tags = ["manual"],
    target_compatible_with = ["@platforms//os:linux"],
    visibility = ["//visibility:public"],
)

sh_test(
    name = "git_linux_x86_64_manifest_test",
    size = "medium",
    srcs = ["//git/test:assert_git_manifest.sh"],
    data = [
        ":git_linux_x86_64",
        "//compile:llvm_minimal_host_llvm_readelf",
    ],
    env = {
        "GIT_VERSION": VERSIONS["git"],
        "GLIBC_FLOOR": "2.28",
        "READELF": "$(rootpath //compile:llvm_minimal_host_llvm_readelf)",
        "TARBALL": "$(rootpath :git_linux_x86_64)",
    },
    tags = ["manual"],
    target_compatible_with = ["@platforms//os:linux"],
)
