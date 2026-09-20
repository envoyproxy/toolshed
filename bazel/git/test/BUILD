load("@rules_shell//shell:sh_test.bzl", "sh_test")
load("//:versions.bzl", "VERSIONS")
load(
    ":git_toolchain_test.bzl",
    "git_toolchain_probe",
    "render_hub_build_test",
    "resolved_repo_test",
    "source_repo_test",
    "source_toolchain_probe",
)

exports_files([
    "assert_git_https.sh",
    "assert_git_manifest.sh",
    "assert_git_toolchain_https.sh",
    "assert_git_toolchain_version.sh",
])

git_toolchain_probe(
    name = "resolved_git",
)

source_toolchain_probe(
    name = "resolved_git_source",
    probe = ":resolved_git",
)

filegroup(
    name = "resolved_git_repo_name",
    srcs = [":resolved_git"],
    output_group = "repo_name",
)

filegroup(
    name = "resolved_git_source_repo_name",
    srcs = [":resolved_git_source"],
    output_group = "repo_name",
)

sh_test(
    name = "git_linux_x86_64_manifest_test",
    size = "medium",
    srcs = [":assert_git_manifest.sh"],
    data = [
        "//compile:llvm_minimal_host_llvm_readelf",
        "//git:git_linux_x86_64",
        "@bsd_tar_toolchains//:resolved_toolchain",
    ],
    env = {
        "GIT_VERSION": VERSIONS["git"],
        "GLIBC_FLOOR": "2.31",
        "READELF": "$(rootpath //compile:llvm_minimal_host_llvm_readelf)",
        "TAR": "$(rootpath @bsd_tar_toolchains//:resolved_toolchain)",
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
        "external",
        "requires-network",
    ],
    target_compatible_with = ["@platforms//os:linux"],
)

sh_test(
    name = "toolchain_version_test",
    size = "small",
    srcs = [":assert_git_toolchain_version.sh"],
    data = [
        ":resolved_git",
        ":resolved_git_repo_name",
    ],
    env = {
        "GIT": "$(rootpath :resolved_git)",
        "GIT_VERSION": VERSIONS["git"],
        "REPO_NAME_FILE": "$(rootpath :resolved_git_repo_name)",
    },
    target_compatible_with = ["@platforms//os:linux"],
)

sh_test(
    name = "toolchain_https_test",
    size = "medium",
    srcs = [":assert_git_toolchain_https.sh"],
    data = [":resolved_git"],
    env = {"GIT": "$(rootpath :resolved_git)"},
    tags = [
        "external",
        "requires-network",
    ],
    target_compatible_with = ["@platforms//os:linux"],
)

sh_test(
    name = "toolchain_source_version_test",
    size = "small",
    srcs = [":assert_git_toolchain_version.sh"],
    data = [
        ":resolved_git_source",
        ":resolved_git_source_repo_name",
    ],
    env = {
        "EXPECT_SOURCE_ONLY": "1",
        "GIT": "$(rootpath :resolved_git_source)",
        "GIT_VERSION": VERSIONS["git"],
        "REPO_NAME_FILE": "$(rootpath :resolved_git_source_repo_name)",
    },
    target_compatible_with = ["@platforms//os:linux"],
)

sh_test(
    name = "toolchain_source_https_test",
    size = "medium",
    srcs = [":assert_git_toolchain_https.sh"],
    data = [":resolved_git_source"],
    env = {"GIT": "$(rootpath :resolved_git_source)"},
    tags = [
        "external",
        "requires-network",
    ],
    target_compatible_with = ["@platforms//os:linux"],
)

resolved_repo_test(
    name = "resolved_git_prebuilt_repo_test",
    expected_repo_name = "git_prebuilt_linux_x86_64",
    target_compatible_with = [
        "@platforms//cpu:x86_64",
        "@platforms//os:linux",
    ],
    target_under_test = ":resolved_git",
)

source_repo_test(
    name = "resolved_git_source_repo_test",
    expected_repo_prefix = "git+",
    target_under_test = ":resolved_git_source",
)

render_hub_build_test(
    name = "render_hub_build_test",
)
