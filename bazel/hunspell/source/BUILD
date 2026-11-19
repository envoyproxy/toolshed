# Source-built hunspell: the toolchain consumers fall back to where there is no prebuilt (eg
# macOS), and toolshed's tests. The published per-platform packages are built on `main`.

load("//hunspell:defs.bzl", "hunspell_toolchain")

hunspell_toolchain(
    name = "source_impl",
    affix = "@dictionary_en//:index.aff",
    dictionary = "@dictionary_en//:index.dic",
    hunspell = "@hunspell_src//:hunspell",
)

# One per supported exec OS: the build overlay assumes POSIX (eg `unistd.h`, `langinfo.h`), so
# elsewhere (eg Windows) resolution fails cleanly rather than selecting a toolchain that cannot
# build.
[
    toolchain(
        name = "source_toolchain_%s" % os,
        exec_compatible_with = ["@platforms//os:%s" % os],
        toolchain = ":source_impl",
        toolchain_type = "//hunspell:toolchain_type",
        visibility = ["//visibility:public"],
    )
    for os in [
        "linux",
        "macos",
    ]
]
