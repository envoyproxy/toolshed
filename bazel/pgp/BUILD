load("@bazel_skylib//:bzl_library.bzl", "bzl_library")
load("@bazel_skylib//rules:common_settings.bzl", "string_flag")
load("//pgp:defs.bzl", "pgp_toolchain", "sq_signer")
load("//pgp/private:sq_package.bzl", "sq_package")
load("//:versions.bzl", "VERSIONS")
load("@rules_shell//shell:sh_test.bzl", "sh_test")

exports_files([
    "defs.bzl",
    "toolchain.bzl",
])

# Ensures the public/private Starlark surface stays loadable and is covered by
# `bazel build //pgp/...`.
bzl_library(
    name = "pgp_bzl",
    srcs = [
        "defs.bzl",
        "toolchain.bzl",
        "//pgp/private:changes.bzl",
        "//pgp/private:public_key.bzl",
        "//pgp/private:sign.bzl",
        "//pgp/private:sq.bzl",
        "//pgp/private:sq_package.bzl",
    ],
    visibility = ["//visibility:private"],
    deps = [
        "//pgp/audit:audit_bzl",
        "@bazel_skylib//rules:common_settings",
    ],
)

# Toolchain type for OpenPGP signer implementations.
#
# The default implementation wraps `@sq//:sq`, built from source via the Envoy
# Bazel registry, but any binary implementing the signer CLI contract documented
# in toolchain.bzl can be registered instead.
toolchain_type(
    name = "toolchain_type",
    visibility = ["//visibility:public"],
)

sq_signer(
    name = "sq_signer",
    sq = "@sq//:sq",
    visibility = ["//pgp/test:__pkg__"],
)

pgp_toolchain(
    name = "sq_signer_toolchain",
    signer = ":sq_signer",
)

toolchain(
    name = "sq_toolchain",
    toolchain = ":sq_signer_toolchain",
    toolchain_type = "//pgp:toolchain_type",
    visibility = ["//visibility:public"],
)

sq_package(
    name = "sq_linux_x86_64",
    platform = "Linux-X64",
    stripper = "//compile:llvm_minimal_host_llvm_strip",
)

sq_package(
    name = "sq_linux_arm64",
    platform = "Linux-ARM64",
    stripper = "//compile:llvm_minimal_host_llvm_strip",
)

filegroup(
    name = "sq_packages",
    srcs = [":sq_linux_x86_64", ":sq_linux_arm64"],
    tags = ["manual"],
    target_compatible_with = ["@platforms//os:linux"],
    visibility = ["//visibility:public"],
)

sh_test(
    name = "sq_linux_x86_64_manifest_test",
    srcs = ["//pgp/test:assert_sq_manifest.sh"],
    data = [
        ":sq_linux_x86_64",
        "//compile:llvm_minimal_host_llvm_readelf",
    ],
    env = {
        "TARBALL": "$(rootpath :sq_linux_x86_64)",
        "READELF": "$(rootpath //compile:llvm_minimal_host_llvm_readelf)",
        "SQ_VERSION": VERSIONS["sq"],
    },
    tags = ["manual"],
)

# Absolute host path of the passphrase-encrypted secret key.
#
# The key is a host path, not an artifact in the build graph: Bazel only ever
# sees the path, never the key file contents. The file is read by the signer at
# execution time.
#
# It must not live under the Bazel output tree or any artifact upload path.
string_flag(
    name = "key_path",
    build_setting_default = "",
    visibility = ["//visibility:public"],
)

# Absolute host path of the file containing the passphrase for the signing
# key.
#
# The passphrase is deliberately *not* part of the build graph: only this
# path is seen by Bazel, and only the path (never the passphrase) appears on
# the signer command line. The file is read by the signer at execution time.
#
# It must not live under the Bazel output tree or any artifact upload path.
string_flag(
    name = "passphrase_path",
    build_setting_default = "",
    visibility = ["//visibility:public"],
)
