"""Repository rules for cross-compilation libc++ libraries."""

load("//:versions.bzl", "VERSIONS")

def _libcxx_cross_impl(ctx):
    """Implementation for libcxx_cross repository rule."""
    target_arch = ctx.attr.target_arch
    supported = ["aarch64", "x86_64"]
    if target_arch not in supported:
        fail("Unsupported target_arch: {}. Supported: {}".format(target_arch, supported))

    ctx.download_and_extract(
        url = "https://github.com/envoyproxy/toolshed/releases/download/bins-v{version}/cross-llvm{llvm_version}-{arch}.tar.xz".format(
            arch = target_arch,
            version = ctx.attr.version,
            llvm_version = VERSIONS["llvm"],
        ),
        sha256 = ctx.attr.sha256,
        stripPrefix = "cross-libs-{}".format(target_arch),
    )

    # Create BUILD file.  The tarball produced by //compiler/cross:cxx_cross_{arch}
    # has a flat lib/ layout matching the cmake install prefix.
    ctx.file("BUILD.bazel", """package(default_visibility = ["//visibility:public"])

cc_library(
    name = "libcxx",
    srcs = ["lib/libc++.a"],
    linkstatic = True,
    alwayslink = True,
)

cc_library(
    name = "libcxxabi",
    srcs = ["lib/libc++abi.a"],
    linkstatic = True,
    alwayslink = True,
)

cc_library(
    name = "libunwind",
    srcs = ["lib/libunwind.a"],
    linkstatic = True,
    alwayslink = True,
)

cc_library(
    name = "libcxx_cross",
    srcs = [
        "lib/libc++.a",
        "lib/libc++abi.a",
        "lib/libunwind.a",
    ],
    linkstatic = True,
    alwayslink = True,
)
""")

libcxx_cross = repository_rule(
    implementation = _libcxx_cross_impl,
    attrs = {
        "target_arch": attr.string(
            mandatory = True,
            doc = "Target architecture (e.g., 'aarch64', 'x86_64')",
        ),
        "version": attr.string(
            mandatory = True,
            doc = "Toolshed bins release version to download (e.g., '0.1.46')",
        ),
        "sha256": attr.string(
            mandatory = True,
            doc = "SHA256 hash of the published cross libs tarball",
        ),
    },
    doc = "Downloads prebuilt libc++, libc++abi, and libunwind from toolshed releases for cross-compilation",
)

def setup_libcxx_cross(
        target_arch,
        version = None,
        sha256 = None):
    """Setup function for WORKSPACE.

    Args:
        target_arch: Target architecture string, e.g. "aarch64" or "x86_64". Mandatory.
        version: Toolshed bins release version. Defaults to VERSIONS["bins_release"].
        sha256: SHA256 of the published tarball. Defaults to VERSIONS["libcxx_cross_sha256"][target_arch].
    """
    libcxx_cross(
        name = "libcxx_cross_{}".format(target_arch),
        target_arch = target_arch,
        version = version or VERSIONS["bins_release"],
        sha256 = sha256 or VERSIONS["libcxx_cross_sha256"][target_arch],
    )


libcxx_cross = repository_rule(
    implementation = _libcxx_cross_impl,
    attrs = {
        "target_arch": attr.string(
            mandatory = True,
            doc = "Target architecture (e.g., 'aarch64', 'x86_64')",
        ),
        "version": attr.string(
            mandatory = True,
            doc = "Toolshed bins release version to download (e.g., '0.1.46')",
        ),
        "sha256": attr.string(
            mandatory = True,
            doc = "SHA256 hash of the published cross libs tarball",
        ),
    },
    doc = "Downloads prebuilt libc++, libc++abi, and libunwind from toolshed releases for cross-compilation",
)

def setup_libcxx_cross(
        target_arch,
        version = None,
        sha256 = None):
    """Setup function for WORKSPACE.

    Args:
        target_arch: Target architecture string, e.g. "aarch64" or "x86_64". Mandatory.
        version: Toolshed bins release version. Defaults to VERSIONS["bins_release"].
        sha256: SHA256 of the published tarball. Defaults to VERSIONS["libcxx_cross_sha256"][target_arch].
    """
    libcxx_cross(
        name = "libcxx_cross_{}".format(target_arch),
        target_arch = target_arch,
        version = version or VERSIONS["bins_release"],
        sha256 = sha256 or VERSIONS["libcxx_cross_sha256"][target_arch],
    )
