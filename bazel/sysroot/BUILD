"""BUILD file for sysroot package.

This package provides Bazel targets for building Debian sysroots for cross-compilation.

IMPORTANT: These are non-hermetic builds that:
  - Require sudo access
  - Use debootstrap and chroot
  - Download packages from Debian mirrors
  - Are marked as 'manual' so they don't build by default
  - Are marked as 'no-cache' and 'no-remote' to prevent caching

These targets are intended for specific purposes and take a while to build,
so they must be explicitly requested.
"""

load("@rules_shell//shell:sh_binary.bzl", "sh_binary")
load(":sysroot_genrule.bzl", "sysroots")

exports_files([
    "sysroot.bzl",
    "sysroot_genrule.bzl",
    "build_sysroot.sh",
])

# Shell binary for building sysroots
# This can be used directly to build custom sysroot configurations
sh_binary(
    name = "build_sysroot",
    srcs = ["build_sysroot.sh"],
    visibility = ["//visibility:public"],
)

# Generate all sysroot targets using a matrix configuration
sysroots([
    # glibc 2.31 (current) - Debian bullseye
    {
        "arch": "amd64",
        "glibc_version": "2.31",
        "debian_version": "bullseye",
        "variant": "base",
    },
    {
        "arch": "arm64",
        "glibc_version": "2.31",
        "debian_version": "bullseye",
        "variant": "base",
    },
    {
        "arch": "amd64",
        "glibc_version": "2.31",
        "debian_version": "bullseye",
        "variant": "libstdcxx",
        "ppa_toolchain": "focal",
        "stdcc_version": "13",
    },
    {
        "arch": "arm64",
        "glibc_version": "2.31",
        "debian_version": "bullseye",
        "variant": "libstdcxx",
        "ppa_toolchain": "focal",
        "stdcc_version": "13",
    },
    # glibc 2.28 (older) - Debian buster for Ubuntu 18.04/RHEL 8 compatibility
    {
        "arch": "amd64",
        "glibc_version": "2.28",
        "debian_version": "buster",
        "variant": "base",
    },
    {
        "arch": "arm64",
        "glibc_version": "2.28",
        "debian_version": "buster",
        "variant": "base",
    },
    {
        "arch": "amd64",
        "glibc_version": "2.28",
        "debian_version": "buster",
        "variant": "libstdcxx",
        "ppa_toolchain": "bionic",
        "stdcc_version": "13",
    },
    {
        "arch": "arm64",
        "glibc_version": "2.28",
        "debian_version": "buster",
        "variant": "libstdcxx",
        "ppa_toolchain": "bionic",
        "stdcc_version": "13",
    },
])
