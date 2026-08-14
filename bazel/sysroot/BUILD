"""BUILD file for sysroot package.

This package provides Bazel targets for building Debian sysroots for cross-compilation.

IMPORTANT: These are non-hermetic builds that:
  - Require sudo access
  - Use debootstrap and chroot
  - Download packages from Debian mirrors
  - Are marked as 'manual' so they don't build by default
  - Use 'no-remote-exec' to stay local but allow remote cache reads/writes
  - Are keyed on a daily UTC stamp so they rebuild at most once per day

These targets are intended for specific purposes and take a while to build,
so they must be explicitly requested.
"""

load("@aspect_bazel_lib//lib:tar.bzl", "mtree_mutate", "mtree_spec", "tar")
load("@rules_shell//shell:sh_binary.bzl", "sh_binary")
load("//:versions.bzl", "VERSIONS")
load(":macos_sysroot.bzl", "macos_sysroot_extract")
load(":fs.bzl", "sysroot_daily_stamp", "sysroots")

exports_files([
    "build_sysroot.sh",
    "config.yaml",
    "extensions.bzl",
    "fs.bzl",
    "macos_sysroot.bzl",
    "sysroot.bzl",
])

ARCHES = ["amd64", "arm64"]
GLIBC = ["2.28", "2.31"]
STDCC = ["13", ""]

sh_binary(
    name = "build_sysroot",
    srcs = ["build_sysroot.sh"],
    visibility = ["//visibility:public"],
)

sysroot_daily_stamp()

sysroots(
    arches = ARCHES,
    glibc = GLIBC,
    stdcc = STDCC,
)

macos_sysroot_extract(
    name = "sysroot_macos_arm64_src",
    sdk_pkg = "@macos_sdk_pkg//:sdk_pkg",
    pkgutil = "@pkgutil_linux_amd64//:pkgutil_bin",
    manifest = "manifests/sysroot-macos.txt",
    sdk_prefix = VERSIONS["macos_sdk_pkg"]["sdk_prefix"],
    tags = ["manual"],
)

mtree_spec(
    name = "sysroot_macos_arm64_mtree_src",
    srcs = [":sysroot_macos_arm64_src"],
    tags = ["manual"],
)

mtree_mutate(
    name = "sysroot_macos_arm64_mtree",
    mtree = ":sysroot_macos_arm64_mtree_src",
    srcs = [":sysroot_macos_arm64_src"],
    strip_prefix = "sysroot/sysroot_macos_arm64_src",
    tags = ["manual"],
)

tar(
    name = "sysroot_macos_arm64",
    compress = "xz",
    mtree = ":sysroot_macos_arm64_mtree",
    out = "sysroot-macos-arm64.tar.xz",
    srcs = [":sysroot_macos_arm64_src"],
    tags = ["manual"],
    visibility = ["//visibility:public"],
)
