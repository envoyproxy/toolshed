"""Repository rules for prebuilt V8 wee8 bundles."""

load("//:versions.bzl", "V8_VERSION", "VERSIONS")

_WEE8_BUILD = """\
package(default_visibility = ["//visibility:public"])

filegroup(
    name = "headers",
    srcs = glob(
        [
            "include/**",
            "third_party/**/*.h",
            "src/**/*.h",
        ],
    ),
)

filegroup(
    name = "libs",
    srcs = ["lib/libwee8.a"],
)

cc_library(
    name = "wee8",
    srcs = ["lib/libwee8.a"],
    hdrs = [":headers"],
    includes = [
        ".",
        "include",
    ],
    linkstatic = True,
)
"""

def _wee8_prebuilt_impl(ctx):
    """Implementation for wee8 prebuilt repository rule."""
    sha256 = ctx.attr.sha256
    if sha256:
        ctx.download_and_extract(
            url = "https://github.com/envoyproxy/toolshed/releases/download/bins-v{version}/v8-wee8-{v8_version}-linux-{arch}.tar.xz".format(
                version = ctx.attr.version,
                v8_version = V8_VERSION,
                arch = ctx.attr.arch,
            ),
            sha256 = sha256,
        )
    else:
        # No hash available yet — create a placeholder archive to keep setup non-fatal
        # until the first release populates versions.bzl.
        ctx.execute(["mkdir", "-p", "include", "lib", "src", "third_party"])
        ctx.file(
            "lib/libwee8.a",
            "Wee8 prebuilt archive not available yet. Run update-versions workflow after a bins release containing wee8 artifacts.\n",
        )

    ctx.file("BUILD.bazel", _WEE8_BUILD)

wee8_prebuilt = repository_rule(
    implementation = _wee8_prebuilt_impl,
    attrs = {
        "version": attr.string(
            mandatory = True,
            doc = "Release version to download",
        ),
        "sha256": attr.string(
            default = "",
            doc = "SHA256 hash of the wee8 archive. Empty string skips download.",
        ),
        "arch": attr.string(
            mandatory = True,
            values = ["x86_64", "aarch64"],
            doc = "Architecture to target",
        ),
    },
    doc = "Downloads prebuilt wee8 bundles for cross-compilation",
)

def setup_wee8_prebuilt(
        x86_64_version = None,
        x86_64_sha256 = None,
        aarch64_version = None,
        aarch64_sha256 = None):
    """Setup function for WORKSPACE."""
    wee8_prebuilt(
        name = "wee8_prebuilt_x86_64",
        version = x86_64_version or VERSIONS["bins_release"],
        sha256 = x86_64_sha256 or VERSIONS.get("wee8_sha256", {}).get("x86_64", ""),
        arch = "x86_64",
    )

    wee8_prebuilt(
        name = "wee8_prebuilt_aarch64",
        version = aarch64_version or VERSIONS["bins_release"],
        sha256 = aarch64_sha256 or VERSIONS.get("wee8_sha256", {}).get("aarch64", ""),
        arch = "aarch64",
    )
