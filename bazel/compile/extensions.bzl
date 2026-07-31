"""Module extension for libcxx and sanitizer libraries configuration in bzlmod."""

load("//:versions.bzl", "LLVM_CXX_BUILD", "SUPPORTED_ARCHES", "VERSIONS")
load(":libcxx_libs.bzl", "setup_libcxx_libs")
load(":llvm_minimal.bzl", "llvm_toolchain_alias", "setup_llvm_minimal", "setup_llvm_minimal_build")
load(":llvm_prebuilt.bzl", "llvm_prebuilt")
load(":sanitizer_libs.bzl", "setup_sanitizer_libs")

def _sanitizer_libs_impl(module_ctx):
    """Implementation of the sanitizer_libs module extension.

    This extension allows configuring sanitizer libraries in MODULE.bazel using
    the same setup_sanitizer_libs() function used in WORKSPACE.
    """

    # Collect all setup tags from all modules
    # Only use the first tag found (sanitizer repos have fixed names)
    setup_tag = None
    for mod in module_ctx.modules:
        for tag in mod.tags.setup:
            if setup_tag == None:
                setup_tag = tag
            else:
                # Fail if multiple tags are found
                fail("Multiple setup() calls found for sanitizer_extension. Only one configuration is allowed since repository names are fixed to @msan_libs and @tsan_libs.")

    # Call setup_sanitizer_libs once with the configuration
    if setup_tag:
        setup_sanitizer_libs(
            msan_version = setup_tag.msan_version,
            msan_sha256 = setup_tag.msan_sha256,
            tsan_version = setup_tag.tsan_version,
            tsan_sha256 = setup_tag.tsan_sha256,
        )
    else:
        # Use default configuration if no tags specified
        setup_sanitizer_libs()

_setup = tag_class(
    attrs = {
        "msan_version": attr.string(
            doc = "Version of MSAN release to use (default: VERSIONS['bins_release'] from //:versions.bzl)",
        ),
        "msan_sha256": attr.string(
            doc = "SHA256 hash of the MSAN libs archive (default: VERSIONS['msan_libs_sha256'] from //:versions.bzl)",
        ),
        "tsan_version": attr.string(
            doc = "Version of TSAN release to use (default: VERSIONS['bins_release'] from //:versions.bzl)",
        ),
        "tsan_sha256": attr.string(
            doc = "SHA256 hash of the TSAN libs archive (default: VERSIONS['tsan_libs_sha256'] from //:versions.bzl)",
        ),
    },
)

sanitizer_extension = module_extension(
    implementation = _sanitizer_libs_impl,
    tag_classes = {
        "setup": _setup,
    },
)

def _libcxx_libs_ext_impl(module_ctx):
    """Implementation of the libcxx_libs module extension.

    This extension allows configuring prebuilt libcxx libraries for cross-compilation
    in MODULE.bazel using the same setup_libcxx_libs() function used in WORKSPACE.
    """

    # Collect all setup tags from all modules
    # Only use the first tag found (libcxx_libs repos have fixed names)
    setup_tag = None
    for mod in module_ctx.modules:
        for tag in mod.tags.setup:
            if setup_tag == None:
                setup_tag = tag
            else:
                fail("Multiple setup() calls found for libcxx_libs_extension. Only one configuration is allowed since repository names are fixed to @libcxx_libs_aarch64 and @libcxx_libs_x86_64.")

    # Call setup_libcxx_libs once with the configuration
    if setup_tag:
        setup_libcxx_libs(
            aarch64_version = setup_tag.aarch64_version,
            aarch64_sha256 = setup_tag.aarch64_sha256,
            x86_64_version = setup_tag.x86_64_version,
            x86_64_sha256 = setup_tag.x86_64_sha256,
        )
    else:
        # Use default configuration if no tags specified
        setup_libcxx_libs()

_libcxx_libs_setup = tag_class(
    attrs = {
        "aarch64_version": attr.string(
            doc = "Version of aarch64 libcxx release to use (default: VERSIONS['bins_release'] from //:versions.bzl)",
        ),
        "aarch64_sha256": attr.string(
            doc = "SHA256 hash of the aarch64 libcxx libs archive (default: VERSIONS['libcxx_libs_sha256']['aarch64'] from //:versions.bzl)",
        ),
        "x86_64_version": attr.string(
            doc = "Version of x86_64 libcxx release to use (default: VERSIONS['bins_release'] from //:versions.bzl)",
        ),
        "x86_64_sha256": attr.string(
            doc = "SHA256 hash of the x86_64 libcxx libs archive (default: VERSIONS['libcxx_libs_sha256']['x86_64'] from //:versions.bzl)",
        ),
    },
)

libcxx_libs_extension = module_extension(
    implementation = _libcxx_libs_ext_impl,
    tag_classes = {
        "setup": _libcxx_libs_setup,
    },
)

def _libcxx_ext_impl(module_ctx):
    for arch in SUPPORTED_ARCHES:
        config = VERSIONS["llvm_libcxx_%s" % arch]
        build_file_content = LLVM_CXX_BUILD.format(**config)
        url = config["url"].format(**config)
        strip_prefix = config["strip_prefix"].format(**config)
        llvm_prebuilt(
            name = "llvm_libcxx_%s" % arch,
            build_file_content = build_file_content,
            sha256 = config["sha256"],
            strip_prefix = strip_prefix,
            url = url,
        )

libcxx_extension = module_extension(
    implementation = _libcxx_ext_impl,
)

# =============================================================================
# llvm_minimal_extension: sets up released llvm_minimal_* repos used by
# consumers and host-tool aliases.
# =============================================================================

def _llvm_minimal_ext_impl(module_ctx):
    """Set up llvm_minimal_* repos for consumers."""
    setup_tag = None
    for mod in module_ctx.modules:
        for tag in mod.tags.setup:
            if setup_tag == None:
                setup_tag = tag
            else:
                fail("Multiple setup() calls found for llvm_minimal_extension. Only one configuration is allowed since repository names are fixed to @llvm_minimal_linux_x64, @llvm_minimal_linux_arm64, and @llvm_minimal_macos_arm64.")

    if setup_tag:
        setup_llvm_minimal(
            linux_x64_sha256 = setup_tag.linux_x64_sha256 or None,
            linux_arm64_sha256 = setup_tag.linux_arm64_sha256 or None,
            macos_arm64_sha256 = setup_tag.macos_arm64_sha256 or None,
        )
    else:
        setup_llvm_minimal()

_llvm_minimal_setup = tag_class(
    attrs = {
        "linux_x64_sha256": attr.string(
            doc = "SHA256 hash of the Linux-X64 minimal LLVM artifact (default: VERSIONS['llvm_minimal_linux_x64']['sha256'] from //:versions.bzl)",
        ),
        "linux_arm64_sha256": attr.string(
            doc = "SHA256 hash of the Linux-ARM64 minimal LLVM artifact (default: VERSIONS['llvm_minimal_linux_arm64']['sha256'] from //:versions.bzl)",
        ),
        "macos_arm64_sha256": attr.string(
            doc = "SHA256 hash of the macOS-ARM64 minimal LLVM artifact (default: VERSIONS['llvm_minimal_macos_arm64']['sha256'] from //:versions.bzl)",
        ),
    },
)

llvm_minimal_extension = module_extension(
    implementation = _llvm_minimal_ext_impl,
    tag_classes = {
        "setup": _llvm_minimal_setup,
    },
)

# =============================================================================
# llvm_minimal_build_extension: sets up raw-tarball download repos needed to
# BUILD the minimal LLVM artifacts (//compile:llvm_minimal_*).
# Use this as a dev_dependency in MODULE.bazel.
# =============================================================================

def _llvm_minimal_build_ext_impl(module_ctx):
    """Set up llvm_tarball_* repos for building minimal LLVM artifacts."""
    setup_llvm_minimal_build()

llvm_minimal_build_extension = module_extension(
    implementation = _llvm_minimal_build_ext_impl,
)

def _llvm_toolchain_alias_ext_impl(module_ctx):
    """Set up the host-arch llvm_toolchain_llvm alias repo."""
    llvm_toolchain_alias(name = "llvm_toolchain_llvm")

llvm_toolchain_alias_extension = module_extension(
    implementation = _llvm_toolchain_alias_ext_impl,
)
