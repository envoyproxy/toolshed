load("@bazel_skylib//:bzl_library.bzl", "bzl_library")
load("@bazel_skylib//rules:common_settings.bzl", "string_flag")
load("@rules_shell//shell:sh_test.bzl", "sh_test")
load("//dependency:reachability.bzl", "dependency_reachability")
load(":custom_rule_test.bzl", "custom_library_rule")
load(":reachability_apparent_name_test.bzl", "apparent_name_test")
load(":reachability_config_validation_test.bzl", "reachability_config_validation_test")
load(":reachability_package_pattern_test.bzl", "reachability_package_pattern_test")
load(":reachability_test_rules.bzl", "dependency_reachability_with_mode")

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

dependency_reachability(
    name = "reachability_empty_attribution_patterns",
    testonly = True,
    roots = [
        ":core_root",
        ":test_root",
    ],
    attribution_patterns = [],
)

string_flag(
    name = "reachability_mode",
    build_setting_default = "default",
    values = ["default", "extra"],
)

config_setting(
    name = "reachability_mode_extra",
    flag_values = {":reachability_mode": "extra"},
)

filegroup(
    name = "variant_external_consumer",
    srcs = [
        "@bazel_skylib//lib:paths",
    ] + select({
        ":reachability_mode_extra": ["@jq_toolchains//:resolved_toolchain"],
        "//conditions:default": [],
    }),
)

filegroup(
    name = "variant_core_root",
    srcs = [":variant_external_consumer"],
)

filegroup(
    name = "variant_test_root",
    testonly = True,
    srcs = [
        ":variant_external_consumer",
        "@bazel_skylib//lib:sets",
    ],
)

dependency_reachability_with_mode(
    name = "reachability_multiconfig",
    testonly = True,
    roots = [
        ":variant_core_root",
        ":variant_test_root",
    ],
    configs = {
        "default": {},
        "extra": {"//dependency/test:reachability_mode": "extra"},
    },
)

filegroup(
    name = "attribution_root",
    srcs = [
        "//dependency/test/transitive/ext/deep:root",
        "//dependency/test/transitive/ext/direct:root",
        "//dependency/test/transitive/ext/one:root",
        "//dependency/test/transitive/ext/two:root",
    ],
)

filegroup(
    name = "attribution_testonly_root",
    testonly = True,
    srcs = ["//dependency/test/transitive/ext/testonly:root"],
)

dependency_reachability(
    name = "reachability_attribution",
    testonly = True,
    roots = [
        ":attribution_root",
        ":attribution_testonly_root",
    ],
    attribution_patterns = ["//dependency/test/transitive/ext/..."],
)

filegroup(
    name = "attribution_variant_root",
    srcs = select({
        ":reachability_mode_extra": ["//dependency/test/transitive/ext/config_extra:root"],
        "//conditions:default": ["//dependency/test/transitive/ext/config_default:root"],
    }),
)

dependency_reachability_with_mode(
    name = "reachability_attribution_multiconfig",
    testonly = True,
    roots = [":attribution_variant_root"],
    attribution_patterns = ["//dependency/test/transitive/ext/..."],
    configs = {
        "default": {},
        "extra": {"//dependency/test:reachability_mode": "extra"},
    },
)

dependency_reachability(
    name = "reachability_attribution_excluded_baseline",
    testonly = True,
    roots = ["//dependency/test/transitive/ext/excluded:root"],
    attribution_patterns = ["//dependency/test/transitive/ext/..."],
)

dependency_reachability(
    name = "reachability_attribution_excluded",
    testonly = True,
    roots = ["//dependency/test/transitive/ext/excluded:root"],
    attribution_patterns = ["//dependency/test/transitive/ext/..."],
    excluded_patterns = ["rules_pkg*"],
)

sh_test(
    name = "reachability_test",
    size = "small",
    srcs = ["reachability_test.sh"],
    data = [
        ":reachability",
        ":reachability_empty_attribution_patterns",
        ":reachability_attribution",
        ":reachability_attribution_multiconfig",
        ":reachability_multiconfig",
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

custom_library_rule(
    name = "excluded_edge_to_skylib",
    library = "@bazel_skylib//lib:paths",
)

custom_library_rule(
    name = "excluded_edge_to_rules_shell",
    library = "@rules_shell//shell:toolchain_type",
)

filegroup(
    name = "excluded_edge_root",
    srcs = [
        ":excluded_edge_to_skylib",
        ":excluded_edge_to_rules_shell",
        "@bazel_skylib//lib:sets",
    ],
)

dependency_reachability(
    name = "reachability_excluded_edge",
    testonly = True,
    roots = [":excluded_edge_root"],
    excluded_edges = ["library"],
)

dependency_reachability(
    name = "reachability_edge_and_pattern",
    testonly = True,
    roots = [":excluded_edge_root"],
    excluded_edges = ["library"],
    excluded_patterns = ["bazel_skylib*"],
)

filegroup(
    name = "pattern_root",
    srcs = [
        "@bazel_skylib//lib:paths",
        "@bazel_tools//tools/bash/runfiles:runfiles",
    ],
)

dependency_reachability(
    name = "reachability_excluded_pattern",
    testonly = True,
    roots = [":pattern_root"],
    excluded_patterns = ["bazel_*"],
)

filegroup(
    name = "rules_pkg_root",
    srcs = ["@rules_pkg//pkg:filter_directory"],
)

dependency_reachability(
    name = "reachability_rules_pkg_transitive",
    testonly = True,
    roots = [":rules_pkg_root"],
)

dependency_reachability(
    name = "reachability_excluded_rules_pkg_transitive",
    testonly = True,
    roots = [":rules_pkg_root"],
    excluded_patterns = ["rules_pkg*"],
)

dependency_reachability(
    name = "reachability_empty_exclusions",
    testonly = True,
    roots = [":core_root"],
)

dependency_reachability(
    name = "reachability_empty_exclusions_explicit",
    testonly = True,
    roots = [":core_root"],
    excluded_edges = [],
    excluded_patterns = [],
)

sh_test(
    name = "exclusions_reachability_test",
    size = "small",
    srcs = ["exclusions_reachability_test.sh"],
    data = [
        ":reachability_excluded_edge",
        ":reachability_edge_and_pattern",
        ":reachability_excluded_pattern",
        ":reachability_rules_pkg_transitive",
        ":reachability_excluded_rules_pkg_transitive",
        ":reachability_empty_exclusions",
        ":reachability_empty_exclusions_explicit",
        ":reachability_attribution_excluded_baseline",
        ":reachability_attribution_excluded",
        "@jq_toolchains//:resolved_toolchain",
    ],
    env = {
        "JQ_BIN": "$(JQ_BIN)",
    },
    toolchains = ["@jq_toolchains//:resolved_toolchain"],
)

bzl_library(
    name = "reachability_apparent_name_test_lib",
    srcs = [
        "reachability_apparent_name_test.bzl",
        "reachability_config_validation_test.bzl",
        "reachability_package_pattern_test.bzl",
        "reachability_test_rules.bzl",
    ],
    deps = [
        "@bazel_skylib//lib:unittest",
    ],
)

apparent_name_test(
    name = "apparent_name_test",
)

reachability_config_validation_test(
    name = "reachability_config_validation_test",
)

reachability_package_pattern_test(
    name = "reachability_package_pattern_test",
)
