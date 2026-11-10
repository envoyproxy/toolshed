load("@bazel_skylib//rules:build_test.bzl", "build_test")
load("@rules_shell//shell:sh_binary.bzl", "sh_binary")
load("@rules_shell//shell:sh_test.bzl", "sh_test")
load("//coverage:lcov_merger.bzl", "lcov_merger")
load("//coverage:macros.bzl", "coverage_report")

licenses(["notice"])  # Apache 2

genrule(
    name = "generated_config",
    srcs = ["testdata/config.json"],
    outs = ["generated_config.json"],
    cmd = "cp $< $@",
)

coverage_report(
    name = "smoke",
    config = ":generated_config",
)

[
    genrule(
        name = "custom_" + template,
        srcs = ["//coverage:templates/" + template + ".html"],
        outs = ["custom_templates/" + template + "/renamed.html"],
        cmd = "cp $< $@",
    )
    for template in [
        "base",
        "index",
        "macros",
    ]
]

coverage_report(
    name = "custom",
    config = ":generated_config",
    source_glob = "*.cpp",
    source_root = "nested/source",
    templates = [
        ":custom_base",
        ":custom_index",
        ":custom_macros",
    ],
)

sh_binary(
    name = "fake_lcov_merge",
    srcs = ["fake_lcov_merge.sh"],
)

coverage_report(
    name = "premerged",
    config = ":generated_config",
    lcov_merge = ":fake_lcov_merge",
)

build_test(
    name = "smoke_build_test",
    targets = [
        ":smoke",
        ":smoke.validate",
        ":custom",
        ":premerged",
        "//coverage:lcov_merger",
        "//coverage:run",
    ],
)

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
    name = "report_generator_test",
    srcs = ["report_generator_test.sh"],
    data = [
        ":custom",
        ":premerged",
        ":smoke",
        "@jq_toolchains//:resolved_toolchain",
        "@zstd//:zstd_cli",
    ] + glob(["testdata/**"]),
    env = {
        "CUSTOM_GENERATOR": "$(rlocationpath :custom)",
        "GENERATOR": "$(rlocationpath :smoke)",
        "PREMERGED_GENERATOR": "$(rlocationpath :premerged)",
        "JQ_BIN": "$(rlocationpath @jq_toolchains//:resolved_toolchain)",
        "LCOV_DATA": "$(rlocationpath testdata/coverage.dat)",
        "ZSTD_BIN": "$(rlocationpath @zstd//:zstd_cli)",
    },
    deps = ["@bazel_tools//tools/bash/runfiles"],
)

[
    sh_test(
        name = name,
        srcs = [name + ".sh"],
        args = ["$(rootpath //coverage:run.sh)"],
        data = ["//coverage:run.sh"],
    )
    for name in [
        "run_sh_args_test",
        "run_test",
    ]
]

sh_test(
    name = "validate_test",
    srcs = ["validate_test.sh"],
    args = [
        "$(rootpath :smoke.validate)",
        "$(rootpath validation/pass.json)",
    ],
    data = [":smoke.validate"] + glob(["validation/*.json"]),
)

sh_test(
    name = "llvm_wrappers_test",
    srcs = ["llvm_wrappers_test.sh"],
    data = ["//coverage:llvm/llvm-cov.sh"],
    env = {"LLVM_COV_WRAPPER": "$(rlocationpath //coverage:llvm/llvm-cov.sh)"},
    deps = ["@bazel_tools//tools/bash/runfiles"],
)
