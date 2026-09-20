load("@rules_shell//shell:sh_test.bzl", "sh_test")
load("//:versions.bzl", "VERSIONS")

exports_files([
    "assert_git_https.sh",
    "assert_git_manifest.sh",
])

sh_test(
    name = "git_linux_x86_64_manifest_test",
    size = "medium",
    srcs = [":assert_git_manifest.sh"],
    data = [
        "//git:git_linux_x86_64",
        "//compile:llvm_minimal_host_llvm_readelf",
        "@bsd_tar_toolchains//:resolved_toolchain",
    ],
    env = {
        "TAR": "$(rootpath @bsd_tar_toolchains//:resolved_toolchain)",
        "GIT_VERSION": VERSIONS["git"],
        "GLIBC_FLOOR": "2.31",
        "READELF": "$(rootpath //compile:llvm_minimal_host_llvm_readelf)",
        "TARBALL": "$(rootpath //git:git_linux_x86_64)",
    },
    target_compatible_with = ["@platforms//os:linux"],
)

sh_test(
    name = "git_linux_x86_64_https_test",
    size = "medium",
    srcs = [":assert_git_https.sh"],
    data = [
        "//git:git_linux_x86_64",
        "@bsd_tar_toolchains//:resolved_toolchain",
    ],
    env = {
        "TAR": "$(rootpath @bsd_tar_toolchains//:resolved_toolchain)",
        "TARBALL": "$(rootpath //git:git_linux_x86_64)",
    },
    tags = [
        "requires-network",
        "external",
    ],
    target_compatible_with = ["@platforms//os:linux"],
)
