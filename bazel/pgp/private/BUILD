load("@rules_shell//shell:sh_binary.bzl", "sh_binary")

exports_files([
    "checksums.sh",
    "signer.sh",
    "sign.bzl",
    "sq.bzl",
])

sh_binary(
    name = "checksums",
    srcs = ["checksums.sh"],
    visibility = ["//visibility:public"],
)
