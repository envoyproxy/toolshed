load("@rules_shell//shell:sh_binary.bzl", "sh_binary")

exports_files([
    "checksums.sh",
    "changes.bzl",
    "public_key.bzl",
    "public_key.sh",
    "signer.sh",
    "sign.bzl",
    "sq.bzl",
    "sq_package.bzl",
])

sh_binary(
    name = "checksums",
    srcs = ["checksums.sh"],
    visibility = ["//visibility:public"],
)

sh_binary(
    name = "public_key_validator",
    srcs = ["public_key.sh"],
    visibility = ["//pgp/test:__pkg__"],
)
