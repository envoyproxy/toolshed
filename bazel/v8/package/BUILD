load("//v8:wee8_package.bzl", "wee8_package", "wee8_package_target_name")

licenses(["notice"])

wee8_package(
    name = wee8_package_target_name("x86_64"),
    arch = "x86_64",
)

wee8_package(
    name = wee8_package_target_name("x86_64", "libstdcxx"),
    arch = "x86_64",
    stdlib = "libstdcxx",
)

filegroup(
    name = "wee8_package_linux_x86_64",
    srcs = [
        ":%s" % wee8_package_target_name("x86_64"),
        ":%s" % wee8_package_target_name("x86_64", "libstdcxx"),
    ],
    tags = ["manual"],
)

wee8_package(
    name = wee8_package_target_name("aarch64"),
    arch = "aarch64",
)

filegroup(
    name = "wee8_package_linux_aarch64",
    srcs = [
        ":%s" % wee8_package_target_name("aarch64"),
    ],
    tags = ["manual"],
)
