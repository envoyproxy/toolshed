load("@bazel_skylib//:bzl_library.bzl", "bzl_library")
load("@rules_shell//shell:sh_test.bzl", "sh_test")
load("//dependency:reachability.bzl", "dependency_reachability")
load(":custom_rule_test.bzl", "custom_library_rule")
load(":reachability_apparent_name_test.bzl", "apparent_name_test")

sh_test(
    name = "updater_test",
    size = "small",
    srcs = ["updater_test.sh"],
    data = [
        "//dependency:bazel-update.sh",
        "testdata/dependency_versions.json",
        "testdata/versions.bzl",
        "@jq_toolchains//:resolved_toolchain",
    ],
    env = {
        "JQ_BIN": "$(JQ_BIN)",
    },
    toolchains = ["@jq_toolchains//:resolved_toolchain"],
)

filegroup(
    name = "external_consumer",
    srcs = ["@bazel_skylib//lib:paths"],
)

filegroup(
    name = "core_root",
    srcs = [":external_consumer"],
)

filegroup(
    name = "test_root",
    testonly = True,
    srcs = [
        ":external_consumer",
        "@bazel_skylib//lib:sets",
    ],
)

dependency_reachability(
    name = "reachability",
    testonly = True,
    roots = [
        ":core_root",
        ":test_root",
    ],
)

sh_test(
    name = "reachability_test",
    size = "small",
    srcs = ["reachability_test.sh"],
    data = [
        ":reachability",
        "@jq_toolchains//:resolved_toolchain",
    ],
    env = {
        "JQ_BIN": "$(JQ_BIN)",
    },
    toolchains = ["@jq_toolchains//:resolved_toolchain"],
)

# ---------------------------------------------------------------------------
# Custom-attribute traversal tests
#
# Verify that the aspect records edges carried on non-standard attribute names
# (e.g. `library`, mirroring v8_lib_no_pointer_compression) and that
# implicit/private (_-prefixed) attributes do not contribute recorded edges.
# ---------------------------------------------------------------------------

# A custom rule that carries its external dep in `library` rather than `deps`.
custom_library_rule(
    name = "custom_lib_consumer",
    library = "@bazel_skylib//lib:shell",
)

# A normal filegroup that reaches custom_lib_consumer transitively via `srcs`,
# confirming that propagation composes across mixed attribute kinds.
filegroup(
    name = "custom_lib_root",
    srcs = [":custom_lib_consumer"],
)

dependency_reachability(
    name = "custom_attr_reachability",
    testonly = True,
    roots = [":custom_lib_root"],
)

sh_test(
    name = "custom_attr_reachability_test",
    size = "small",
    srcs = ["custom_attr_reachability_test.sh"],
    data = [
        ":custom_attr_reachability",
        "@jq_toolchains//:resolved_toolchain",
    ],
    env = {
        "JQ_BIN": "$(JQ_BIN)",
    },
    toolchains = ["@jq_toolchains//:resolved_toolchain"],
)

bzl_library(
    name = "reachability_apparent_name_test_lib",
    srcs = ["reachability_apparent_name_test.bzl"],
    deps = [
        "@bazel_skylib//lib:unittest",
    ],
)

apparent_name_test(
    name = "apparent_name_test",
)
