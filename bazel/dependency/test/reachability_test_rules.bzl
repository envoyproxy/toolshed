load("//dependency:reachability.bzl", "dependency_reachability_rule")

dependency_reachability_with_mode = dependency_reachability_rule(
    flags = ["//dependency/test:reachability_mode"],
)
