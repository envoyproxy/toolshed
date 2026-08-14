load("//v8:wee8_package.bzl", "wee8_package", "wee8_package_target_name")

licenses(["notice"])

WEE8_VARIANTS = [
    ("x86_64", "libcxx"),
    ("aarch64", "libcxx"),
    ("x86_64", "libstdcxx"),
]

[
    wee8_package(arch = arch, stdlib = stdlib)
    for arch, stdlib in WEE8_VARIANTS
]

filegroup(
    name = "wee8_packages",
    srcs = [
        ":%s" % wee8_package_target_name(arch, stdlib)
        for arch, stdlib in WEE8_VARIANTS
    ],
    tags = ["manual"],
    target_compatible_with = ["@platforms//os:linux"],
    visibility = ["//visibility:public"],
)
