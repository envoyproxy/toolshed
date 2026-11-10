load(":lcov_merge_repository.bzl", "LCOV_MERGE_PLATFORMS")

licenses(["notice"])  # Apache 2

exports_files([
    "extensions.bzl",
    "lcov_merge_repository.bzl",
])

# One per platform the prebuilt lcov-merge exists for; coverage_report selects on these.
[
    config_setting(
        name = platform,
        constraint_values = constraints,
        visibility = ["//visibility:public"],
    )
    for platform, constraints in LCOV_MERGE_PLATFORMS.items()
]
