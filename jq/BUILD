load("@bazel_skylib//rules:diff_test.bzl", "diff_test")
load(":defs.bzl", "jq_module_test", "test_modules", "toolshed_jq")

exports_files(glob(["**/*.jq"]) + [
    "run-tests.sh",
    "modules_root.marker",
])

filegroup(
    name = "modules",
    srcs = glob(["**/*.jq"]),
    visibility = ["//visibility:public"],
)

[
    jq_module_test(
        name = "test_%s" % module.replace("/", "_"),
        module = module,
    )
    for module in test_modules(glob(["tests/**/*.test.yml"]))
]

toolshed_jq(
    name = "toolshed_jq_smoke",
    srcs = [],
    out = "toolshed_jq_smoke.txt",
    filter = 'import "str" as str; "  x  " | str::trim',
    args = ["-r"],
)

diff_test(
    name = "toolshed_jq_smoke_test",
    file1 = ":toolshed_jq_smoke",
    file2 = "testdata/toolshed_jq_smoke.expected.txt",
)
