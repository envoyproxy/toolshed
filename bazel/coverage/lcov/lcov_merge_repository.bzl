"""Repository rule for the prebuilt `lcov-merge` binary."""

load("@bazel_tools//tools/build_defs/repo:utils.bzl", "maybe")
load("//:versions.bzl", "VERSIONS")

# The version of rust/lcov published in the bins release.
LCOV_MERGE_VERSION = "0.1.0"

# Platforms the bins release carries lcov-merge for. `//coverage/lcov` has a config_setting
# per entry, and coverage_report only hands the merger to the report on those platforms.
LCOV_MERGE_PLATFORMS = {
    "amd64": ["@platforms//os:linux", "@platforms//cpu:x86_64"],
    "arm64": ["@platforms//os:linux", "@platforms//cpu:aarch64"],
}

def _platform(rctx):
    os_name = rctx.os.name
    arch = rctx.os.arch
    if os_name == "linux":
        if arch in ("x86_64", "amd64"):
            return "amd64"
        if arch in ("aarch64", "arm64"):
            return "arm64"
    return None

_BUILD = """
load("@rules_shell//shell:sh_binary.bzl", "sh_binary")

exports_files(["lcov-merge"])

filegroup(
    name = "lcov_merge_bin",
    srcs = ["lcov-merge"],
    visibility = ["//visibility:public"],
)

sh_binary(
    name = "lcov_merge",
    srcs = ["lcov-merge"],
    visibility = ["//visibility:public"],
)
"""

# Assembled rather than written out so the shebang does not get this file linted as shell.
_UNAVAILABLE = "#!/bin/sh\n" + "\n".join([
    'echo "lcov-merge: no prebuilt binary for {os} {arch}; coverage_report merges with grcov on this platform" >&2',
    "exit 1",
    "",
])

def _lcov_merge_repo_impl(rctx):
    platform = _platform(rctx)
    if platform == None:
        # Never fail the fetch: the repository is loaded wherever the label is mentioned,
        # and coverage_report does not use the merger on these platforms.
        rctx.file(
            "lcov-merge",
            _UNAVAILABLE.format(os = rctx.os.name, arch = rctx.os.arch),
            executable = True,
        )
    else:
        rctx.download(
            url = "https://github.com/envoyproxy/toolshed/releases/download/bins-v{version}/lcov-merge-{lcov_merge_version}-{arch}".format(
                version = rctx.attr.bins_release_version,
                lcov_merge_version = LCOV_MERGE_VERSION,
                arch = platform,
            ),
            sha256 = VERSIONS["lcov_merge_sha256"].get(platform, ""),
            output = "lcov-merge",
            executable = True,
        )
    rctx.file("BUILD.bazel", _BUILD)

_lcov_merge_repo = repository_rule(
    implementation = _lcov_merge_repo_impl,
    attrs = {
        "bins_release_version": attr.string(
            doc = "Version of the toolshed bins release to download from",
            mandatory = True,
        ),
    },
)

def lcov_merge_repository(bins_release_version):
    """Download the `lcov-merge` binary for the current platform as `@lcov_merge`.

    Args:
        bins_release_version: Version of the bins release (e.g., "0.2.31")
    """
    maybe(
        _lcov_merge_repo,
        name = "lcov_merge",
        bins_release_version = bins_release_version,
    )
