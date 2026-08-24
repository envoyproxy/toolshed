load(
    "//dependency:reachability.bzl",
    "dependency_reachability_macro",
    "dependency_reachability_rule",
)

_dependency_reachability_with_mode = dependency_reachability_rule(
    flags = ["//dependency/test:reachability_mode"],
)

dependency_reachability_with_mode = dependency_reachability_macro(_dependency_reachability_with_mode)
