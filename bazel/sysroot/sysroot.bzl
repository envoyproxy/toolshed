"""Repository rules for sysroots."""

load("//:versions.bzl", "VERSIONS")

def _get_platform_arch(ctx):
    """Get the platform architecture for sysroot selection."""
    arch = ctx.os.arch
    if arch == "x86_64" or arch == "amd64":
        return "amd64"
    elif arch == "aarch64" or arch == "arm64":
        return "arm64"
    else:
        fail("Unsupported architecture: {}".format(arch))

def _sysroot_impl(ctx):
    """Implementation for sysroot repository rule."""
    arch = ctx.attr.arch or _get_platform_arch(ctx)
    glibc_version = ctx.attr.glibc_version
    stdcc_version = ctx.attr.stdcc_version

    # Construct URL based on whether stdcc_version is specified
    if stdcc_version:
        url = "https://github.com/envoyproxy/toolshed/releases/download/bins-v{version}/sysroot-glibc{glibc_version}-libstdc++{stdcc_version}-{arch}.tar.xz".format(
            version = ctx.attr.version,
            arch = arch,
            glibc_version = glibc_version,
            stdcc_version = stdcc_version,
        )
    else:
        url = "https://github.com/envoyproxy/toolshed/releases/download/bins-v{version}/sysroot-glibc{glibc_version}-{arch}.tar.xz".format(
            version = ctx.attr.version,
            arch = arch,
            glibc_version = glibc_version,
        )

    ctx.download_and_extract(
        url = url,
        sha256 = ctx.attr.sha256,
        stripPrefix = "",
    )
    ctx.file("BUILD.bazel", """
package(default_visibility = ["//visibility:public"])

filegroup(
    name = "sysroot",
    srcs = glob(
        ["**"],
        exclude = [
            "**/*:*",
            "**/*.pl",
        ],
    ),
)

filegroup(
    name = "headers",
    srcs = glob(
        ["usr/include/**"],
        exclude = ["**/*:*"],
    ),
)

filegroup(
    name = "libs",
    srcs = glob(
        [
            "usr/lib/**/*.a",
            "usr/lib/**/*.so*",
            "lib/**/*.a",
            "lib/**/*.so*",
        ],
        exclude = ["**/*:*"],
    ),
)

filegroup(
    name = "toolchain_sysroot",
    srcs = [":sysroot"],
)
""")

sysroot = repository_rule(
    implementation = _sysroot_impl,
    attrs = {
        "version": attr.string(
            mandatory = True,
            doc = "Release version to download (e.g., '1.0.0')",
        ),
        "sha256": attr.string(
            mandatory = True,
            doc = "SHA256 hash of the sysroot archive",
        ),
        "arch": attr.string(
            doc = "Architecture to download (amd64 or arm64). If not specified, uses host architecture",
        ),
        "glibc_version": attr.string(
            mandatory = True,
            doc = "glibc version (e.g., '2.31' or '2.28')",
        ),
        "stdcc_version": attr.string(
            doc = "libstdc++ version (e.g., '13'). If not specified, base sysroot without libstdc++ is used",
        ),
    },
    doc = "Downloads sysroot for the specified or host architecture",
)

def _get_sysroot_hash(glibc_version, stdcc_version, arch):
    """Get the SHA256 hash for a specific sysroot configuration.

    Args:
        glibc_version: glibc version (e.g., "2.31" or "2.28")
        stdcc_version: libstdc++ version (e.g., "13") or None for base sysroot
        arch: Architecture (e.g., "amd64" or "arm64")

    Returns:
        SHA256 hash string
    """

    # Validate glibc version
    if glibc_version not in VERSIONS["sysroot_hashes"]:
        fail("Unsupported glibc version: {}. Supported versions: {}".format(
            glibc_version,
            ", ".join(VERSIONS["sysroot_hashes"].keys()),
        ))

    # Determine stdlib variant key
    stdlib_variant = stdcc_version if stdcc_version else "base"

    # Validate stdlib variant
    if stdlib_variant not in VERSIONS["sysroot_hashes"][glibc_version]:
        fail("Unsupported libstdc++ version '{}' for glibc {}. Supported variants: {}".format(
            stdcc_version or "base",
            glibc_version,
            ", ".join(VERSIONS["sysroot_hashes"][glibc_version].keys()),
        ))

    # Validate architecture
    if arch not in VERSIONS["sysroot_hashes"][glibc_version][stdlib_variant]:
        fail("Unsupported architecture '{}' for glibc {} with libstdc++ {}. Supported architectures: {}".format(
            arch,
            glibc_version,
            stdcc_version or "base",
            ", ".join(VERSIONS["sysroot_hashes"][glibc_version][stdlib_variant].keys()),
        ))

    # Get the hash
    sha256 = VERSIONS["sysroot_hashes"][glibc_version][stdlib_variant][arch]

    # Validate hash is not empty
    if not sha256:
        fail("SHA256 hash not yet available for glibc {} with libstdc++ {} on {}. This configuration may not be released yet.".format(
            glibc_version,
            stdcc_version or "base",
            arch,
        ))

    return sha256

_MACOS_SYSROOT_BUILD = """\
package(default_visibility = ["//visibility:public"])

filegroup(
    name = "sysroot",
    srcs = glob(
        ["**"],
        exclude = ["**/*:*"],
    ),
)
"""

def _macos_sysroot_impl(ctx):
    """Implementation for macOS SDK sysroot repository rule."""
    if ctx.os.name.startswith("mac"):
        # On macOS, no cross-compilation sysroot needed.
        ctx.file("BUILD.bazel", _MACOS_SYSROOT_BUILD)
        return

    sha256 = ctx.attr.sha256
    if sha256:
        url = "https://github.com/envoyproxy/toolshed/releases/download/bins-v{version}/sysroot-macos-{arch}.tar.xz".format(
            version = ctx.attr.version,
            arch = ctx.attr.arch,
        )
        ctx.download_and_extract(
            url,
            sha256 = sha256,
        )
    else:
        # No hash available yet — create an empty sysroot.
        ctx.execute(["mkdir", "-p", "usr/include"])

    ctx.file("BUILD.bazel", _MACOS_SYSROOT_BUILD)

macos_sysroot = repository_rule(
    implementation = _macos_sysroot_impl,
    attrs = {
        "version": attr.string(
            mandatory = True,
            doc = "Release version to download",
        ),
        "sha256": attr.string(
            default = "",
            doc = "SHA256 hash of the macOS sysroot archive. Empty string skips download.",
        ),
        "arch": attr.string(
            default = "arm64",
            doc = "Architecture (arm64)",
        ),
    },
    doc = "Downloads macOS SDK sysroot for cross-compilation from Linux",
)

def setup_macos_sysroot(version = None):
    """Set up macOS arm64 sysroot for cross-compilation.

    Creates @sysroot_macos_arm64 repository.
    """
    sha256 = VERSIONS.get("macos_sysroot_sha256", {}).get("arm64", "")
    if "sysroot_macos_arm64" not in native.existing_rules():
        macos_sysroot(
            name = "sysroot_macos_arm64",
            version = version or VERSIONS["bins_release"],
            sha256 = sha256,
            arch = "arm64",
        )

def setup_sysroots(
        version = None,
        glibc_version = "2.31",
        stdcc_version = "13",
        name_prefix = ""):
    """Setup function for WORKSPACE to configure sysroots.

    Args:
        version: Version of sysroot release to use (default: uses VERSIONS["bins_release"])
        glibc_version: glibc version to use (default: "2.31", also available: "2.28")
        stdcc_version: libstdc++ version to use (default: "13", set to None for base sysroot)
        name_prefix: Optional prefix for sysroot repository names (default: "")
                    Allows multiple sysroot setups, e.g., name_prefix="old" creates
                    @old_sysroot_linux_amd64 and @old_sysroot_linux_arm64
    """

    # Get hashes from versions.bzl based on configuration
    amd64_sha256 = _get_sysroot_hash(glibc_version, stdcc_version, "amd64")
    arm64_sha256 = _get_sysroot_hash(glibc_version, stdcc_version, "arm64")

    # Construct repository names with optional prefix
    if name_prefix:
        amd64_name = "{}_sysroot_linux_amd64".format(name_prefix)
        arm64_name = "{}_sysroot_linux_arm64".format(name_prefix)
    else:
        amd64_name = "sysroot_linux_amd64"
        arm64_name = "sysroot_linux_arm64"

    # AMD64 sysroot
    sysroot(
        name = amd64_name,
        version = version or VERSIONS["bins_release"],
        sha256 = amd64_sha256,
        arch = "amd64",
        glibc_version = glibc_version,
        stdcc_version = stdcc_version,
    )

    # ARM64 sysroot
    sysroot(
        name = arm64_name,
        version = version or VERSIONS["bins_release"],
        sha256 = arm64_sha256,
        arch = "arm64",
        glibc_version = glibc_version,
        stdcc_version = stdcc_version,
    )
