load(":defs.bzl", "jq_module_test")

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
    for module in [
        "args",
        "bazel/aquery",
        "clang/tidy",
        "github/gfm",
        "str",
        "utils",
        "validate",
    ]
]
