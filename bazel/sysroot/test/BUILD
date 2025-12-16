"""Test BUILD file demonstrating sysroot_build rule usage."""

load("//sysroot:sysroot.bzl", "sysroot_build")

# Example: Build a base sysroot with glibc 2.31
# This is just an example and won't be built by default
sysroot_build(
    name = "example_sysroot_base",
    arch = "amd64",
    glibc_version = "2.31",
    debian_version = "bullseye",
    variant = "base",
    tags = ["manual"],  # Prevent building in CI
)

# Example: Build a sysroot with libstdc++13
sysroot_build(
    name = "example_sysroot_libstdcxx",
    arch = "amd64",
    glibc_version = "2.31",
    debian_version = "bullseye",
    variant = "libstdcxx",
    ppa_toolchain = "focal",
    stdcc_version = "13",
    tags = ["manual"],  # Prevent building in CI
)
