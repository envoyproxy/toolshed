load("@rules_shell//shell:sh_binary.bzl", "sh_binary")
load("@rules_shell//shell:sh_test.bzl", "sh_test")
load("//coverage:lcov_merger.bzl", "lcov_merger")

licenses(["notice"])  # Apache 2

sh_binary(
    name = "fake_merger",
    srcs = ["fake_merger.sh"],
)

lcov_merger(
    name = "fake_lcov_merger",
    merger = ":fake_merger",
)

sh_test(
    name = "lcov_merger_test",
    srcs = ["lcov_merger_test.sh"],
    data = [
        "testdata/per_test.dat",
        ":fake_lcov_merger",
    ],
    env = {
        "LCOV_DATA": "$(rlocationpath testdata/per_test.dat)",
        "MERGER": "$(rlocationpath :fake_lcov_merger)",
    },
    deps = ["@bazel_tools//tools/bash/runfiles"],
)

sh_test(
    name = "lcov_merger_java_test",
    srcs = ["lcov_merger_java_test.sh"],
    data = [
        "testdata/per_test.dat",
        "//coverage:lcov_merger",
    ],
    env = {
        "LCOV_DATA": "$(rlocationpath testdata/per_test.dat)",
        "MERGER": "$(rlocationpath //coverage:lcov_merger)",
    },
    deps = ["@bazel_tools//tools/bash/runfiles"],
)

sh_test(
    name = "llvm_wrappers_test",
    srcs = ["llvm_wrappers_test.sh"],
    data = ["//coverage:llvm/llvm-cov.sh"],
    env = {"LLVM_COV_WRAPPER": "$(rlocationpath //coverage:llvm/llvm-cov.sh)"},
    deps = ["@bazel_tools//tools/bash/runfiles"],
)
