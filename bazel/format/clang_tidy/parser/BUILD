load("@aspect_bazel_lib//lib:jq.bzl", "jq")

exports_files([
    "parse_clang_tidy.jq",
    "parse_clang_tidy.sh",
])

sh_binary(
    name = "parse_clang_tidy",
    srcs = ["parse_clang_tidy.sh"],
    data = [
        "parse_clang_tidy.jq",
        "@jq_toolchains//:resolved_toolchain",
    ],
    visibility = ["//visibility:public"],
)

sh_test(
    name = "parse_clang_tidy_test",
    size = "small",
    srcs = ["tests/run_tests.sh"],
    data = [
        "parse_clang_tidy.jq",
        "parse_clang_tidy.sh",
        "@jq_toolchains//:resolved_toolchain",
    ] + glob([
        "tests/*.txt",
        "tests/*.json",
    ]),
)
