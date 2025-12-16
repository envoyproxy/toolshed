"""Repository rules and build rules for sysroots."""

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

# Build rule for generating sysroots

def _sysroot_build_impl(ctx):
    """Implementation for sysroot build rule."""
    output = ctx.outputs.output
    
    # Prepare arguments for the build script
    args = ctx.actions.args()
    args.add("--arch", ctx.attr.arch)
    args.add("--glibc-version", ctx.attr.glibc_version)
    args.add("--debian-version", ctx.attr.debian_version)
    args.add("--variant", ctx.attr.variant)
    args.add("--output", output.path)
    
    if ctx.attr.variant == "libstdcxx":
        if not ctx.attr.ppa_toolchain or not ctx.attr.stdcc_version:
            fail("libstdcxx variant requires ppa_toolchain and stdcc_version")
        args.add("--ppa-toolchain", ctx.attr.ppa_toolchain)
        args.add("--stdcc-version", ctx.attr.stdcc_version)
    
    # Run the build script
    ctx.actions.run_shell(
        outputs = [output],
        inputs = [ctx.file._build_script],
        command = "{script} {args}".format(
            script = ctx.file._build_script.path,
            args = " ".join([
                "--arch", ctx.attr.arch,
                "--glibc-version", ctx.attr.glibc_version,
                "--debian-version", ctx.attr.debian_version,
                "--variant", ctx.attr.variant,
                "--output", output.path,
            ] + (
                ["--ppa-toolchain", ctx.attr.ppa_toolchain, "--stdcc-version", ctx.attr.stdcc_version]
                if ctx.attr.variant == "libstdcxx" and ctx.attr.ppa_toolchain and ctx.attr.stdcc_version
                else []
            )),
        ),
        mnemonic = "BuildSysroot",
        progress_message = "Building sysroot for {} ({})".format(ctx.attr.arch, ctx.attr.variant),
        use_default_shell_env = True,
        execution_requirements = {
            "requires-network": "1",
            "no-sandbox": "1",  # debootstrap requires filesystem access
            "no-cache": "1",    # sysroot builds should not be cached
        },
    )
    
    return [DefaultInfo(files = depset([output]))]

sysroot_build = rule(
    implementation = _sysroot_build_impl,
    attrs = {
        "arch": attr.string(
            mandatory = True,
            doc = "Architecture to build for (amd64 or arm64)",
        ),
        "glibc_version": attr.string(
            mandatory = True,
            doc = "glibc version (e.g., '2.31' or '2.28')",
        ),
        "debian_version": attr.string(
            mandatory = True,
            doc = "Debian version to base on (e.g., 'bullseye' or 'buster')",
        ),
        "variant": attr.string(
            mandatory = True,
            values = ["base", "libstdcxx"],
            doc = "Variant to build (base or libstdcxx)",
        ),
        "ppa_toolchain": attr.string(
            doc = "PPA toolchain version for libstdc++ (e.g., 'focal' or 'bionic'). Required for libstdcxx variant",
        ),
        "stdcc_version": attr.string(
            doc = "libstdc++ version (e.g., '13'). Required for libstdcxx variant",
        ),
        "_build_script": attr.label(
            default = Label("//sysroot:build_sysroot.sh"),
            allow_single_file = True,
            doc = "Build script for creating sysroots",
        ),
    },
    outputs = {
        "output": "%{name}.tar.xz",
    },
    doc = "Builds a sysroot using debootstrap. Requires debootstrap to be installed and may require elevated permissions.",
)
