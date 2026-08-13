"""Tests for bazel/toolchains/utils.bzl proto toolchain helpers.

These tests require the protobuf proto toolchain to be registered, which is
provided via the `bazel_dep(name = "protobuf", ...)` dev dependency in
MODULE.bazel.

Run with bzlmod enabled (the default when this module is built directly):
    bazel test //toolchains/test/...

WORKSPACE mode: protobuf and its transitive dependencies are not wired into
the WORKSPACE build of this module; these tests are tagged 'manual' to
avoid failing `bazel test //...` under the workspace mode that CI also runs.
To add WORKSPACE support, add com_google_protobuf + its transitive deps
(abseil-cpp, zlib, …) to archives.bzl / WORKSPACE — that is out of scope
for this PR.
"""

load("@rules_shell//shell:sh_test.bzl", "sh_test")
load("//toolchains:utils.bzl", "proto_compiler_binary")
load(":proto_compiler_test_rule.bzl", "proto_compiler_version")

# ---------------------------------------------------------------------------
# Shared expected protoc version.
# Derived from the `protobuf` bazel_dep version in MODULE.bazel:
#   "35.1.bcr.envoy"  →  libprotoc 35.1.x
# Asserted on major.minor only to tolerate patch-level differences.
# Bump this constant when the protobuf bazel_dep version changes.
# ---------------------------------------------------------------------------
EXPECTED_PROTOC_VERSION = "libprotoc 35.1"

# ---------------------------------------------------------------------------
# Test 1: genrule / $(location) consumer path
#
# Instantiates proto_compiler_binary as a runnable target, then invokes it
# from a genrule using $(location) — exactly how downstream genrule consumers
# (e.g. envoy/api) use it.  A sh_test asserts the version string.
# ---------------------------------------------------------------------------

proto_compiler_binary(
    name = "protoc",
    tags = ["manual"],
    visibility = ["//visibility:private"],
)

genrule(
    name = "protoc_version_via_genrule",
    outs = ["protoc_version_genrule.txt"],
    cmd = "$(location :protoc) --version > $@",
    tags = ["manual"],
    tools = [":protoc"],
)

sh_test(
    name = "genrule_protoc_version_test",
    size = "small",
    srcs = ["check_protoc_version.sh"],
    args = [
        "$(rootpath :protoc_version_via_genrule)",
        EXPECTED_PROTOC_VERSION,
    ],
    data = [":protoc_version_via_genrule"],
    tags = ["manual"],
)

# ---------------------------------------------------------------------------
# Test 2: custom rule / use_proto_toolchain() + get_proto_compiler() path
#
# proto_compiler_version uses use_proto_toolchain() and get_proto_compiler()
# directly (the same path used by aspects and rules), independent of the
# proto_compiler_binary convenience target.  A sh_test asserts the version.
# ---------------------------------------------------------------------------

proto_compiler_version(
    name = "rule_version_output",
    tags = ["manual"],
)

sh_test(
    name = "rule_protoc_version_test",
    size = "small",
    srcs = ["check_protoc_version.sh"],
    args = [
        "$(rootpath :rule_version_output)",
        EXPECTED_PROTOC_VERSION,
    ],
    data = [":rule_version_output"],
    tags = ["manual"],
)
