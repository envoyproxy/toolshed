load(":defs.bzl", "jq_module_test", "test_modules")

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
