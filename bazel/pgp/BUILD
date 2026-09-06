load("@bazel_skylib//:bzl_library.bzl", "bzl_library")
load("@bazel_skylib//rules:common_settings.bzl", "string_flag")

exports_files([
    "defs.bzl",
    "toolchain.bzl",
    "extensions.bzl",
])

# Ensures //pgp:extensions.bzl (not otherwise loaded - no `sq` platform is
# enabled by default) and the rest of the public/private starlark surface
# stay loadable and are covered by `bazel build //pgp/...`.
bzl_library(
    name = "pgp_bzl",
    srcs = [
        "defs.bzl",
        "extensions.bzl",
        "toolchain.bzl",
        "//pgp/private:sign.bzl",
        "//pgp/private:sq.bzl",
    ],
    visibility = ["//visibility:private"],
    deps = [
        "//pgp/audit:audit_bzl",
        "@bazel_skylib//rules:common_settings",
    ],
)

# Toolchain type for OpenPGP signer implementations.
#
# The default implementation wraps Sequoia PGP's `sq` (see extensions.bzl),
# but any binary implementing the signer CLI contract documented in
# toolchain.bzl can be registered instead.
toolchain_type(
    name = "toolchain_type",
    visibility = ["//visibility:public"],
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
