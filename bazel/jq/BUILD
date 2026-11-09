exports_files(glob(["**/*.jq"]) + [
    "defs.bzl",
    "launcher.sh.tpl",
    "modules_root.marker",
])

filegroup(
    name = "modules",
    srcs = glob(["**/*.jq"]),
    visibility = ["//visibility:public"],
)
