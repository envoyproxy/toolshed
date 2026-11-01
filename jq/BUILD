load("@bazel_skylib//rules:diff_test.bzl", "diff_test")
load("@rules_jq//jq:defs.bzl", "jq_binary", "jq_library")
load(":defs.bzl", "jq_module_test", "test_modules", "toolshed_jq")

exports_files(glob(["**/*.jq"]) + [
    "defs.bzl",
    "run-tests.sh",
    "modules_root.marker",
])

filegroup(
    name = "modules",
    srcs = glob(["**/*.jq"]),
    visibility = ["//visibility:public"],
)

# The modules as a `rules_jq` library, importable by their scoped path, eg
# `import "github/gfm" as gfm;`.
jq_library(
    name = "library",
    srcs = [":modules"],
    visibility = ["//visibility:public"],
)

# jq with the modules importable: run it in place of jq, eg
# `"$JQ_BIN" -n 'import "str" as str; ...'`.
jq_binary(
    name = "jq",
    deps = [":library"],
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
    args = ["-r"],
    filter = 'import "str" as str; "  x  " | str::trim',
)

diff_test(
    name = "toolshed_jq_smoke_test",
    file1 = ":toolshed_jq_smoke",
    file2 = "testdata/toolshed_jq_smoke.expected.txt",
)

# No filter: the identity filter over `srcs`, as with `jq()`.
toolshed_jq(
    name = "toolshed_jq_identity",
    srcs = ["testdata/toolshed_jq_identity.json"],
    out = "toolshed_jq_identity.out.json",
    args = ["-c"],
)

diff_test(
    name = "toolshed_jq_identity_test",
    file1 = ":toolshed_jq_identity",
    file2 = "testdata/toolshed_jq_identity.json",
)
