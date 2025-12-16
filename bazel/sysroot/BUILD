"""BUILD file for sysroot package."""

load("@rules_shell//shell:sh_binary.bzl", "sh_binary")

exports_files([
    "sysroot.bzl",
    "build_sysroot.sh",
])

# Shell binary for building sysroots
# This can be used directly to build custom sysroot configurations
sh_binary(
    name = "build_sysroot",
    srcs = ["build_sysroot.sh"],
    visibility = ["//visibility:public"],
)

# glibc 2.31 (current) - Debian bullseye base sysroots
genrule(
    name = "sysroot_glibc2.31_amd64",
    srcs = [":build_sysroot"],
    outs = ["sysroot-glibc2.31-amd64.tar.xz"],
    cmd = """
        cd $$(dirname $(location :build_sysroot))
        $(location :build_sysroot) --arch amd64 --glibc 2.31 --debian bullseye --variant base --output $$(mktemp -d)/sysroot-build
        mv sysroot-glibc2.31-amd64.tar.xz $@
    """,
    tags = [
        "manual",
        "no-cache",
        "no-remote",
    ],
    visibility = ["//visibility:public"],
)

genrule(
    name = "sysroot_glibc2.31_arm64",
    srcs = [":build_sysroot"],
    outs = ["sysroot-glibc2.31-arm64.tar.xz"],
    cmd = """
        cd $$(dirname $(location :build_sysroot))
        $(location :build_sysroot) --arch arm64 --glibc 2.31 --debian bullseye --variant base --output $$(mktemp -d)/sysroot-build
        mv sysroot-glibc2.31-arm64.tar.xz $@
    """,
    tags = [
        "manual",
        "no-cache",
        "no-remote",
    ],
    visibility = ["//visibility:public"],
)

# glibc 2.31 (current) - Debian bullseye with libstdc++13
genrule(
    name = "sysroot_glibc2.31_libstdcxx_amd64",
    srcs = [":build_sysroot"],
    outs = ["sysroot-glibc2.31-libstdc++13-amd64.tar.xz"],
    cmd = """
        cd $$(dirname $(location :build_sysroot))
        $(location :build_sysroot) --arch amd64 --glibc 2.31 --debian bullseye --variant libstdcxx --ppa-toolchain focal --stdcc 13 --output $$(mktemp -d)/sysroot-build
        mv sysroot-glibc2.31-libstdc++13-amd64.tar.xz $@
    """,
    tags = [
        "manual",
        "no-cache",
        "no-remote",
    ],
    visibility = ["//visibility:public"],
)

genrule(
    name = "sysroot_glibc2.31_libstdcxx_arm64",
    srcs = [":build_sysroot"],
    outs = ["sysroot-glibc2.31-libstdc++13-arm64.tar.xz"],
    cmd = """
        cd $$(dirname $(location :build_sysroot))
        $(location :build_sysroot) --arch arm64 --glibc 2.31 --debian bullseye --variant libstdcxx --ppa-toolchain focal --stdcc 13 --output $$(mktemp -d)/sysroot-build
        mv sysroot-glibc2.31-libstdc++13-arm64.tar.xz $@
    """,
    tags = [
        "manual",
        "no-cache",
        "no-remote",
    ],
    visibility = ["//visibility:public"],
)

# glibc 2.28 (older) - Debian buster base sysroots for Ubuntu 18.04/RHEL 8 compatibility
genrule(
    name = "sysroot_glibc2.28_amd64",
    srcs = [":build_sysroot"],
    outs = ["sysroot-glibc2.28-amd64.tar.xz"],
    cmd = """
        cd $$(dirname $(location :build_sysroot))
        $(location :build_sysroot) --arch amd64 --glibc 2.28 --debian buster --variant base --output $$(mktemp -d)/sysroot-build
        mv sysroot-glibc2.28-amd64.tar.xz $@
    """,
    tags = [
        "manual",
        "no-cache",
        "no-remote",
    ],
    visibility = ["//visibility:public"],
)

genrule(
    name = "sysroot_glibc2.28_arm64",
    srcs = [":build_sysroot"],
    outs = ["sysroot-glibc2.28-arm64.tar.xz"],
    cmd = """
        cd $$(dirname $(location :build_sysroot))
        $(location :build_sysroot) --arch arm64 --glibc 2.28 --debian buster --variant base --output $$(mktemp -d)/sysroot-build
        mv sysroot-glibc2.28-arm64.tar.xz $@
    """,
    tags = [
        "manual",
        "no-cache",
        "no-remote",
    ],
    visibility = ["//visibility:public"],
)

# glibc 2.28 (older) - Debian buster with libstdc++13
genrule(
    name = "sysroot_glibc2.28_libstdcxx_amd64",
    srcs = [":build_sysroot"],
    outs = ["sysroot-glibc2.28-libstdc++13-amd64.tar.xz"],
    cmd = """
        cd $$(dirname $(location :build_sysroot))
        $(location :build_sysroot) --arch amd64 --glibc 2.28 --debian buster --variant libstdcxx --ppa-toolchain bionic --stdcc 13 --output $$(mktemp -d)/sysroot-build
        mv sysroot-glibc2.28-libstdc++13-amd64.tar.xz $@
    """,
    tags = [
        "manual",
        "no-cache",
        "no-remote",
    ],
    visibility = ["//visibility:public"],
)

genrule(
    name = "sysroot_glibc2.28_libstdcxx_arm64",
    srcs = [":build_sysroot"],
    outs = ["sysroot-glibc2.28-libstdc++13-arm64.tar.xz"],
    cmd = """
        cd $$(dirname $(location :build_sysroot))
        $(location :build_sysroot) --arch arm64 --glibc 2.28 --debian buster --variant libstdcxx --ppa-toolchain bionic --stdcc 13 --output $$(mktemp -d)/sysroot-build
        mv sysroot-glibc2.28-libstdc++13-arm64.tar.xz $@
    """,
    tags = [
        "manual",
        "no-cache",
        "no-remote",
    ],
    visibility = ["//visibility:public"],
)
