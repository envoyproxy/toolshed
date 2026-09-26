load("@bazel_skylib//:bzl_library.bzl", "bzl_library")
load("@bazel_skylib//rules:common_settings.bzl", "bool_flag", "string_flag", "string_list_flag")
load("//dependency:macros.bzl", "module_deps_json", "module_updater", "registry_updater", "updater")

exports_files([
    "README.md",
    "bazel-update.sh",
    "macros.bzl",
    "module-update.sh",
    "reachability.bzl",
    "registry-resolve.sh",
    "registry.bzl",
    "registry_bazelrc.sh",
])

bzl_library(
    name = "registry_bzl",
    srcs = ["registry.bzl"],
    visibility = ["//visibility:private"],
)

bool_flag(
    name = "registry_allow_unsafe",
    build_setting_default = False,
    visibility = ["//visibility:public"],
)

string_flag(
    name = "registry_sha",
    build_setting_default = "",
    visibility = ["//visibility:public"],
)

# Private build settings used by reachability.bzl to transport exclusion lists
# through the configuration transition (including the exec-config transition).
# These are not part of the public API; use dependency_reachability's
# excluded_edges / excluded_patterns attributes instead.
string_list_flag(
    name = "_excluded_edges",
    build_setting_default = [],
    visibility = ["//visibility:public"],
)

string_list_flag(
    name = "_excluded_patterns",
    build_setting_default = [],
    visibility = ["//visibility:public"],
)

string_list_flag(
    name = "_attribution_patterns",
    build_setting_default = [],
    visibility = ["//visibility:public"],
)

updater(
    name = "update",
    dependencies = "//:dependency_versions",
    version_file = "//:versions.bzl",
)

registry_updater(
    name = "update_registry",
    bazelrc = "//:.bazelrc",
)

module_deps_json(
    name = "toolshed_module_deps",
    lockfile = "//:MODULE.bazel.lock",
    module_file = "//:MODULE.bazel",
    visibility = ["//visibility:private"],
)

module_updater(
    name = "update_module",
    bazelrc = "//:.bazelrc",
    dependencies = ":toolshed_module_deps",
    module_file = "//:MODULE.bazel",
)
