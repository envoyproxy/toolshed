load("//v8:wee8_package.bzl", "wee8_package", "wee8_package_target_name")

licenses(["notice"])

_ARCHES = ["x86_64", "aarch64"]
_STDLIBS = ["libcxx", "libstdcxx"]

[
    wee8_package(
        name = wee8_package_target_name(arch, stdlib),
        arch = arch,
        stdlib = stdlib,
    )
    for arch in _ARCHES
    for stdlib in _STDLIBS
]

filegroup(
    name = "wee8_packages",
    srcs = [
        ":%s" % wee8_package_target_name(arch, stdlib)
        for arch in _ARCHES
        for stdlib in _STDLIBS
    ],
    tags = ["manual"],
    target_compatible_with = ["@platforms//os:linux"],
    visibility = ["//visibility:public"],
)
