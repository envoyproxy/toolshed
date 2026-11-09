load("@rules_shell//shell:sh_binary.bzl", "sh_binary")
load(":lcov_merger.bzl", "lcov_merger")
load(":macros.bzl", "COVERAGE_ZSTD_TARGET")

licenses(["notice"])  # Apache 2

exports_files([
    "lcov_merger.bzl",
    "lcov_merger.sh",
    "llvm/llvm-cov.sh",
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

# `--coverage_output_generator=@envoy_toolshed//coverage:lcov_merger`: Bazel's per-test
# merger, minus the function and branch records the report never reads.
lcov_merger(
    name = "lcov_merger",
    visibility = ["//visibility:public"],
)

# `--coverage_support=@envoy_toolshed//coverage:llvm_support` with
# `--test_env=LLVM_COV=external/<envoy_toolshed>/coverage/llvm/llvm-cov.sh`: Bazel's coverage
# postprocessing exports with this in place of the toolchain's llvm-cov (see the script).
filegroup(
    name = "llvm_support",
    srcs = ["llvm/llvm-cov.sh"],
    visibility = ["//visibility:public"],
)
