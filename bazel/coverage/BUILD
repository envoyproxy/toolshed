load(":lcov_merger.bzl", "lcov_merger")

licenses(["notice"])  # Apache 2

exports_files([
    "lcov_merger.bzl",
    "lcov_merger.sh",
    "llvm/llvm-cov.sh",
])

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
