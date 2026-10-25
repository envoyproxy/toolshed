load("@rules_shell//shell:sh_test.bzl", "sh_test")
load(":sysroot_test.bzl", "sysroot_build_test", "sysroot_test")

sysroot_build_test(
    name = "sysroot_build_test",
    target_under_test = "//sysroot:sysroots",
)

sh_test(
    name = "build_sysroot_options_test",
    srcs = ["build_sysroot_options_test.sh"],
    args = ["$(location //sysroot:build_sysroot.sh)"],
    data = ["//sysroot:build_sysroot.sh"],
)

[
    sysroot_test(
        name = "linux_%s_test" % arch,
        headers = "@sysroot_linux_%s//:headers" % arch,
        libs = "@sysroot_linux_%s//:libs" % arch,
        stdio = "@sysroot_linux_%s//sysroot:usr/include/stdio.h" % arch,
        sysroot = "@sysroot_linux_%s//:sysroot" % arch,
        toolchain_sysroot = "@sysroot_linux_%s//:toolchain_sysroot" % arch,
    )
    for arch in [
        "amd64",
        "arm64",
    ]
]

sysroot_test(
    name = "macos_empty_test",
    sysroot = "@sysroot_macos_empty//:sysroot",
)
