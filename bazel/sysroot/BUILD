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
load(":sysroot_genrule.bzl", "sysroots_from_config")
load(":config.bzl", "SYSROOT_CONFIG")

exports_files([
    "sysroot.bzl",
    "sysroot_genrule.bzl",
    "build_sysroot.sh",
    "config.yaml",
    "yaml_to_bzl.sh",
])

# Generate config.bzl from config.yaml
# Run this target to regenerate config.bzl after editing config.yaml:
#   bazel build //sysroot:config_bzl
genrule(
    name = "config_bzl",
    srcs = ["config.yaml"],
    outs = ["config.bzl.generated"],
    cmd = "$(location :yaml_to_bzl.sh) $(location config.yaml) $@",
    tools = [":yaml_to_bzl.sh"],
    message = "Generating config.bzl from config.yaml",
)

# Shell binary for building sysroots
# This can be used directly to build custom sysroot configurations
sh_binary(
    name = "build_sysroot",
    srcs = ["build_sysroot.sh"],
    visibility = ["//visibility:public"],
)

# Generate all sysroot targets from config.yaml
# The config is loaded from config.bzl
sysroots_from_config(SYSROOT_CONFIG)
