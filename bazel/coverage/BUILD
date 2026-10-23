load("@rules_shell//shell:sh_binary.bzl", "sh_binary")
load(":macros.bzl", "COVERAGE_ZSTD_TARGET")

licenses(["notice"])  # Apache 2

exports_files([
    "macros.bzl",
    "report_generator.sh",
    "run.sh",
    "validate.sh",
] + glob(["templates/*.html"]))

sh_binary(
    name = "run",
    srcs = ["run.sh"],
    env = {"COVERAGE_ZSTD_TARGET": COVERAGE_ZSTD_TARGET},
    visibility = ["//visibility:public"],
)
