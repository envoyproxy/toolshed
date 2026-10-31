# Source-built hunspell for toolshed's own builds/tests, and the published per-platform
# packages (`//hunspell/source:hunspell_packages`). Consumers use the prebuilt toolchains.

load("//hunspell:defs.bzl", "hunspell_toolchain")
load("//hunspell/private:hunspell_package.bzl", "hunspell_package")

hunspell_toolchain(
    name = "source_impl",
    affix = "@dictionary_en//:index.aff",
    dictionary = "@dictionary_en//:index.dic",
    hunspell = "@hunspell_src//:hunspell",
)

toolchain(
    name = "source_toolchain",
    toolchain = ":source_impl",
    toolchain_type = "//hunspell:toolchain_type",
    visibility = ["//visibility:public"],
)

[
    hunspell_package(
        name = "hunspell_%s" % platform.replace("-", "_"),
        affix = "@dictionary_en//:index.aff",
        dictionary = "@dictionary_en//:index.dic",
        hunspell = "@hunspell_src//:hunspell",
        licenses = {
            "@dictionary_en//:license": "dictionary-en/license",
            "@hunspell_src//:COPYING": "hunspell/COPYING",
            "@hunspell_src//:COPYING.LESSER": "hunspell/COPYING.LESSER",
            "@hunspell_src//:COPYING.MPL": "hunspell/COPYING.MPL",
        },
        platform = platform,
        stripper = "//compile:llvm_minimal_host_llvm_strip",
        visibility = ["//hunspell/test:__pkg__"],
    )
    for platform in [
        "linux-aarch64",
        "linux-x86_64",
    ]
]

filegroup(
    name = "hunspell_packages",
    srcs = [
        ":hunspell_linux_aarch64",
        ":hunspell_linux_x86_64",
    ],
    tags = ["manual"],
    target_compatible_with = ["@platforms//os:linux"],
    visibility = ["//visibility:public"],
)
