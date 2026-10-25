load(":sysroot_test.bzl", "sysroot_build_test", "sysroot_hashes_test", "sysroot_test")

sysroot_build_test(
    name = "sysroot_build_test",
    target_under_test = "//sysroot:sysroots",
)

sysroot_hashes_test(
    name = "sysroot_hashes_test",
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

[
    sysroot_test(
        name = "libstdcxx_linux_%s_test" % arch,
        headers = "@libstdcxx_sysroot_linux_%s//:headers" % arch,
        libs = "@libstdcxx_sysroot_linux_%s//:libs" % arch,
        stdcc_version = "13",
        stdio = "@libstdcxx_sysroot_linux_%s//sysroot:usr/include/stdio.h" % arch,
        sysroot = "@libstdcxx_sysroot_linux_%s//:sysroot" % arch,
        toolchain_sysroot = "@libstdcxx_sysroot_linux_%s//:toolchain_sysroot" % arch,
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
