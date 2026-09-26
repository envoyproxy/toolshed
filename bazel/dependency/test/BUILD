load("@bazel_skylib//:bzl_library.bzl", "bzl_library")
load("@bazel_skylib//rules:common_settings.bzl", "string_flag")
load("@bazel_skylib//rules:diff_test.bzl", "diff_test")
load("@rules_shell//shell:sh_test.bzl", "sh_test")
load("//dependency:macros.bzl", "module_deps_json")
load("//dependency:reachability.bzl", "dependency_reachability")
load("//dependency:registry.bzl", "registry_bazelrc", "repo_registry")
load(":custom_rule_test.bzl", "custom_library_rule")
load(":fixtures.bzl", "module_updater_fixture")
load(":reachability_apparent_name_test.bzl", "apparent_name_test")
load(":reachability_config_validation_test.bzl", "reachability_config_validation_test")
load(":reachability_package_pattern_test.bzl", "reachability_package_pattern_test")
load(":reachability_test_rules.bzl", "dependency_reachability_with_mode")
load(":registry_test.bzl", "repo_registry_action_test", "repo_registry_runtime_inputs_test", "repo_registry_toolchain_test")

sh_test(
    name = "updater_test",
    size = "small",
    srcs = ["updater_test.sh"],
    data = [
        "testdata/dependency_versions.json",
        "testdata/versions.bzl",
        "//dependency:bazel-update.sh",
        "@jq_toolchains//:resolved_toolchain",
    ],
    env = {
        "JQ_BIN": "$(JQ_BIN)",
    },
    toolchains = ["@jq_toolchains//:resolved_toolchain"],
)

sh_test(
    name = "version_jq_test",
    size = "small",
    srcs = ["version_jq_test.sh"],
    data = [
        "//dependency:jq_libs",
        "version_compare.jq",
        "version_sort.jq",
        "@jq_toolchains//:resolved_toolchain",
    ],
    env = {"JQ_BIN": "$(JQ_BIN)"},
    toolchains = ["@jq_toolchains//:resolved_toolchain"],
)

genrule(
    name = "registries_json",
    srcs = [
        "testdata/module/report.bazelrc.template",
        "testdata/module/registry_bcr/REGISTRY_MARKER",
        "testdata/module/registry_envoy/REGISTRY_MARKER",
        "//dependency:registries.jq",
    ],
    outs = ["registries.json"],
    cmd = """
set -euo pipefail
bcr_root="$$(dirname $(execpath testdata/module/registry_bcr/REGISTRY_MARKER))"
envoy_root="$$(dirname $(execpath testdata/module/registry_envoy/REGISTRY_MARKER))"
sed \
  -e "s|__REGISTRY_BCR__|$$bcr_root|g" \
  -e "s|__REGISTRY_ENVOY__|$$envoy_root|g" \
  $(execpath testdata/module/report.bazelrc.template) \
  | $(execpath @jq_toolchains//:resolved_toolchain) -Rsc --argjson extra '[]' -f $(execpath //dependency:registries.jq) \
  | $(execpath @jq_toolchains//:resolved_toolchain) -S . \
  | sed \
  -e "s|$$bcr_root/|REGISTRY_BCR/|g" \
  -e "s|$$envoy_root/|REGISTRY_ENVOY/|g" > "$@"
""",
    tools = ["@jq_toolchains//:resolved_toolchain"],
)

diff_test(
    name = "registries_jq_test",
    file1 = ":registries_json",
    file2 = "testdata/module/registries.expected.json",
)

module_updater_fixture(
    name = "module_update_bazel_skylib",
    out = "module_update_bazel_skylib.bazel",
    args = ["bazel_skylib"],
)

module_updater_fixture(
    name = "module_report",
    out = "module_report.json",
    args = [
        "--report",
        "--json-out=$$tmpdir/report.json",
    ],
)

genrule(
    name = "module_report_normalized",
    srcs = [
        ":module_report",
        "testdata/module/report.bazelrc.template",
        "testdata/module/registry_bcr/REGISTRY_MARKER",
        "testdata/module/registry_envoy/REGISTRY_MARKER",
    ],
    outs = ["module_report.normalized.json"],
    cmd = """
set -euo pipefail
bcr_root="$$(dirname $(execpath testdata/module/registry_bcr/REGISTRY_MARKER))"
envoy_root="$$(dirname $(execpath testdata/module/registry_envoy/REGISTRY_MARKER))"
sed \
  -e "s|$$bcr_root/|REGISTRY_BCR/|g" \
  -e "s|$$envoy_root/|REGISTRY_ENVOY/|g" \
  $(execpath :module_report) | $(execpath @jq_toolchains//:resolved_toolchain) -S . > "$@"
""",
    tools = ["@jq_toolchains//:resolved_toolchain"],
)

diff_test(
    name = "module_report_test",
    file1 = ":module_report_normalized",
    file2 = "testdata/module/report.expected.json",
)

diff_test(
    name = "module_update_bazel_skylib_test",
    file1 = ":module_update_bazel_skylib",
    file2 = "testdata/module/MODULE.expected.bazel_skylib.bazel",
)

module_updater_fixture(
    name = "module_update_protobuf",
    out = "module_update_protobuf.bazel",
    args = ["protobuf"],
)

diff_test(
    name = "module_update_protobuf_test",
    file1 = ":module_update_protobuf",
    file2 = "testdata/module/MODULE.expected.protobuf.bazel",
)

module_updater_fixture(
    name = "module_update_sq",
    out = "module_update_sq.bazel",
    args = ["sq=1.5.0.envoy"],
)

diff_test(
    name = "module_update_sq_test",
    file1 = ":module_update_sq",
    file2 = "testdata/module/MODULE.expected.sq.bazel",
)

module_deps_json(
    name = "module_deps_json_fixture",
    lockfile = "testdata/module/MODULE.bazel.lock",
    module_file = "testdata/module/MODULE.deps_json.bazel",
)

diff_test(
    name = "module_deps_json_test",
    file1 = ":module_deps_json_fixture",
    file2 = "testdata/module/module_deps.expected.json",
)

sh_test(
    name = "module_deps_json_duplicate_test",
    size = "small",
    srcs = ["module_deps_json_duplicate_test.sh"],
    data = [
        "testdata/module/MODULE.duplicate.lock",
        "//dependency:jq_libs",
        "@jq_toolchains//:resolved_toolchain",
    ],
    env = {"JQ_BIN": "$(JQ_BIN)"},
    toolchains = ["@jq_toolchains//:resolved_toolchain"],
)

sh_test(
    name = "module_deps_json_missing_lock_test",
    size = "small",
    srcs = ["module_deps_json_missing_lock_test.sh"],
    data = [
        "testdata/module/MODULE.bazel.lock",
        "testdata/module/module_deps_missing_lock.declared.txt",
        "//dependency:jq_libs",
        "@jq_toolchains//:resolved_toolchain",
    ],
    env = {"JQ_BIN": "$(JQ_BIN)"},
    toolchains = ["@jq_toolchains//:resolved_toolchain"],
)

sh_test(
    name = "module_deps_json_missing_version_test",
    size = "small",
    srcs = ["module_deps_json_missing_version_test.sh"],
    data = [
        "testdata/module/MODULE.bazel.lock",
        "testdata/module/module_deps_missing_version.declared.txt",
        "//dependency:jq_libs",
        "@jq_toolchains//:resolved_toolchain",
    ],
    env = {"JQ_BIN": "$(JQ_BIN)"},
    toolchains = ["@jq_toolchains//:resolved_toolchain"],
)

sh_test(
    name = "module_deps_json_missing_override_module_name_test",
    size = "small",
    srcs = ["module_deps_json_missing_override_module_name_test.sh"],
    data = [
        "testdata/module/MODULE.bazel.lock",
        "//dependency:jq_libs",
        "@jq_toolchains//:resolved_toolchain",
    ],
    env = {"JQ_BIN": "$(JQ_BIN)"},
    toolchains = ["@jq_toolchains//:resolved_toolchain"],
)

sh_test(
    name = "module_updater_failure_test",
    size = "small",
    srcs = ["module_updater_failure_test.sh"],
    data = [
        "testdata/module/MODULE.template.bazel",
        "testdata/module/deps.template.json",
        "testdata/module/registry_bcr/REGISTRY_MARKER",
        "testdata/module/registry_bcr/modules/aspect_bazel_lib/metadata.json",
        "testdata/module/registry_bcr/modules/bazel_skylib/metadata.json",
        "testdata/module/registry_bcr/modules/protobuf/metadata.json",
        "testdata/module/registry_envoy/REGISTRY_MARKER",
        "testdata/module/registry_envoy/modules/protobuf/metadata.json",
        "testdata/module/registry_envoy/modules/sq/metadata.json",
        "testdata/module/report.bazelrc.template",
        "//dependency:jq_libs",
        "//dependency:module-update.sh",
        "@buildifier//:buildozer",
        "@jq_toolchains//:resolved_toolchain",
    ],
    env = {
        "BUILDOZER": "$(rootpath @buildifier//:buildozer)",
        "JQ_BIN": "$(JQ_BIN)",
    },
    toolchains = ["@jq_toolchains//:resolved_toolchain"],
)

sh_test(
    name = "module_updater_live_test",
    size = "medium",
    srcs = ["module_updater_live_test.sh"],
    data = [
        "//dependency:jq_libs",
        "//dependency:module-update.sh",
        "@jq_toolchains//:resolved_toolchain",
    ],
    env = {"JQ_BIN": "$(JQ_BIN)"},
    tags = [
        "external",
        "manual",
        "requires-network",
    ],
    target_compatible_with = ["@platforms//os:linux"],
    toolchains = ["@jq_toolchains//:resolved_toolchain"],
)

registry_bazelrc(
    name = "rewritten",
    bazelrc = "testdata/registry.bazelrc",
    registry = "testdata/resolved.txt",
    url = "https://raw.githubusercontent.com/envoyproxy/bazel-registry",
)

diff_test(
    name = "registry_bazelrc_test",
    file1 = ":rewritten",
    file2 = "testdata/registry.expected.bazelrc",
)

sh_test(
    name = "registry_bazelrc_failure_test",
    size = "small",
    srcs = ["registry_bazelrc_failure_test.sh"],
    data = [
        "testdata/registry.missing.bazelrc",
        "testdata/resolved.txt",
        "//dependency:registry_bazelrc.sh",
    ],
)

repo_registry(
    name = "resolved_registry",
    repo = "https://github.com/envoyproxy/bazel-registry.git",
    tags = ["manual"],
    url = "https://raw.githubusercontent.com/envoyproxy/bazel-registry",
)

repo_registry_action_test(
    name = "repo_registry_action_test",
    target_under_test = ":resolved_registry",
)

repo_registry_runtime_inputs_test(
    name = "repo_registry_runtime_inputs_test",
    target_under_test = ":resolved_registry",
)

repo_registry_toolchain_test(
    name = "repo_registry_toolchain_test",
)

sh_test(
    name = "repo_registry_live_test",
    size = "medium",
    srcs = ["repo_registry_live_test.sh"],
    data = [":resolved_registry"],
    env = {"RESOLVED": "$(rootpath :resolved_registry)"},
    tags = [
        "external",
        "requires-network",
    ],
    target_compatible_with = ["@platforms//os:linux"],
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
    attribution_patterns = [],
    roots = [
        ":core_root",
        ":test_root",
    ],
)

string_flag(
    name = "reachability_mode",
    build_setting_default = "default",
    values = [
        "default",
        "extra",
    ],
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
    configs = {
        "default": {},
        "extra": {"//dependency/test:reachability_mode": "extra"},
    },
    roots = [
        ":variant_core_root",
        ":variant_test_root",
    ],
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
    attribution_patterns = ["//dependency/test/transitive/ext/..."],
    roots = [
        ":attribution_root",
        ":attribution_testonly_root",
    ],
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
    attribution_patterns = ["//dependency/test/transitive/ext/..."],
    configs = {
        "default": {},
        "extra": {"//dependency/test:reachability_mode": "extra"},
    },
    roots = [":attribution_variant_root"],
)

dependency_reachability(
    name = "reachability_attribution_excluded_baseline",
    testonly = True,
    attribution_patterns = ["//dependency/test/transitive/ext/..."],
    roots = ["//dependency/test/transitive/ext/excluded:root"],
)

dependency_reachability(
    name = "reachability_attribution_excluded",
    testonly = True,
    attribution_patterns = ["//dependency/test/transitive/ext/..."],
    excluded_patterns = ["rules_pkg*"],
    roots = ["//dependency/test/transitive/ext/excluded:root"],
)

sh_test(
    name = "reachability_test",
    size = "small",
    srcs = ["reachability_test.sh"],
    data = [
        ":reachability",
        ":reachability_attribution",
        ":reachability_attribution_multiconfig",
        ":reachability_empty_attribution_patterns",
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
        ":excluded_edge_to_rules_shell",
        ":excluded_edge_to_skylib",
        "@bazel_skylib//lib:sets",
    ],
)

dependency_reachability(
    name = "reachability_excluded_edge",
    testonly = True,
    excluded_edges = ["library"],
    roots = [":excluded_edge_root"],
)

dependency_reachability(
    name = "reachability_edge_and_pattern",
    testonly = True,
    excluded_edges = ["library"],
    excluded_patterns = ["bazel_skylib*"],
    roots = [":excluded_edge_root"],
)

filegroup(
    name = "pattern_root",
    srcs = [
        "@bazel_skylib//lib:paths",
        "@bazel_tools//tools/bash/runfiles",
    ],
)

dependency_reachability(
    name = "reachability_excluded_pattern",
    testonly = True,
    excluded_patterns = ["bazel_*"],
    roots = [":pattern_root"],
)

filegroup(
    name = "apparent_exclusion_root",
    srcs = ["@apparent_excluded_repo//:direct"],
)

dependency_reachability(
    name = "reachability_apparent_exclusion_baseline",
    testonly = True,
    roots = [":apparent_exclusion_root"],
)

dependency_reachability(
    name = "reachability_apparent_exclusion",
    testonly = True,
    excluded_patterns = ["apparent_excluded_repo"],
    roots = [":apparent_exclusion_root"],
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
    excluded_patterns = ["rules_pkg*"],
    roots = [":rules_pkg_root"],
)

dependency_reachability(
    name = "reachability_empty_exclusions",
    testonly = True,
    roots = [":core_root"],
)

dependency_reachability(
    name = "reachability_empty_exclusions_explicit",
    testonly = True,
    excluded_edges = [],
    excluded_patterns = [],
    roots = [":core_root"],
)

sh_test(
    name = "exclusions_reachability_test",
    size = "small",
    srcs = ["exclusions_reachability_test.sh"],
    data = [
        ":reachability_apparent_exclusion",
        ":reachability_apparent_exclusion_baseline",
        ":reachability_attribution_excluded",
        ":reachability_attribution_excluded_baseline",
        ":reachability_edge_and_pattern",
        ":reachability_empty_exclusions",
        ":reachability_empty_exclusions_explicit",
        ":reachability_excluded_edge",
        ":reachability_excluded_pattern",
        ":reachability_excluded_rules_pkg_transitive",
        ":reachability_rules_pkg_transitive",
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
        "reachability_test_extension.bzl",
        "reachability_test_rules.bzl",
    ],
    deps = [
        "@bazel_skylib//lib:unittest",
    ],
)

bzl_library(
    name = "registry_test_lib",
    srcs = ["registry_test.bzl"],
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
