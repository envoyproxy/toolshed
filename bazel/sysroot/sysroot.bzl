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

    # When cross-compiling for arm64 from an x86_64 host, overlay aarch64
    # libc++/libc++abi/libunwind from the LLVM aarch64 distribution into the
    # sysroot so that the toolchain can link with libc++ instead of libstdc++.
    #
    # libc++ is preferred over libstdc++ to match native x86_64 builds (which
    # use builtin-libc++) and to avoid duplicate operator new/delete symbol
    # conflicts with TCMalloc when statically linking libstdc++.a.
    #
    # On aarch64 hosts the native LLVM toolchain already provides libc++ for
    # aarch64 targets, so the overlay is skipped.
    if arch == "arm64" and ctx.os.arch != "aarch64":
        _overlay_libcxx_arm64(ctx)

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

def _overlay_libcxx_arm64(ctx):
    """Overlays aarch64 libc++ from the LLVM distribution into the sysroot.

    Extracts libc++.a, libc++abi.a, libunwind.a and the arch-specific
    __config_site header from the official LLVM aarch64-linux-gnu tarball
    into usr/lib/aarch64-linux-gnu/ and usr/include/ respectively.
    """
    llvm_ver = VERSIONS["llvm"]
    llvm_sha256 = VERSIONS["llvm_aarch64_sha256"][llvm_ver]
    llvm_strip_prefix = "clang+llvm-{ver}-aarch64-linux-gnu".format(ver = llvm_ver)
    llvm_lib_subdir = "aarch64-unknown-linux-gnu"
    llvm_libs = ["libc++.a", "libc++abi.a", "libunwind.a"]
    llvm_url = "https://github.com/llvm/llvm-project/releases/download/llvmorg-{ver}/clang+llvm-{ver}-aarch64-linux-gnu.tar.xz".format(ver = llvm_ver)

    ctx.download(
        llvm_url,
        output = "_llvm_aarch64.tar.xz",
        sha256 = llvm_sha256,
        executable = False,
    )

    result = ctx.execute(["mkdir", "-p", "usr/lib/aarch64-linux-gnu"])
    if result.return_code != 0:
        fail("mkdir failed: " + result.stderr)

    # Strip prefix_components + "lib/" + "{triple}/" = prefix_parts + 2
    num_strip = len(llvm_strip_prefix.split("/")) + 2
    tar_args = [
        "tar",
        "-xf",
        "_llvm_aarch64.tar.xz",
        "--strip-components",
        str(num_strip),
        "-C",
        "usr/lib/aarch64-linux-gnu",
    ] + [
        llvm_strip_prefix + "/lib/" + llvm_lib_subdir + "/" + lib
        for lib in llvm_libs
    ]
    result = ctx.execute(tar_args)
    if result.return_code != 0:
        fail("Failed to extract LLVM libs:\n" + result.stderr)

    # Extract the aarch64-specific __config_site (arch-specific libc++ config).
    # Placed at usr/include/__config_site so clang finds it via the sysroot
    # include path without extra -isystem flags.
    config_site_path = (
        llvm_strip_prefix + "/include/" + llvm_lib_subdir + "/c++/v1/__config_site"
    )
    result = ctx.execute([
        "tar",
        "-xf",
        "_llvm_aarch64.tar.xz",
        "--strip-components",
        str(len(llvm_strip_prefix.split("/")) + 4),
        "-C",
        "usr/include",
        config_site_path,
    ])
    if result.return_code != 0:
        fail("Failed to extract __config_site:\n" + result.stderr)

    ctx.execute(["rm", "_llvm_aarch64.tar.xz"])

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
