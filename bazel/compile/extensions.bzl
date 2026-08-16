"""Module extension for libcxx and sanitizer libraries configuration in bzlmod."""

load(":libcxx_libs.bzl", "setup_libcxx_libs")
load(":llvm_minimal.bzl", "llvm_toolchain_alias", "setup_llvm_minimal", "setup_llvm_minimal_build")
load(":llvm_prebuilt.bzl", "setup_llvm_prebuilt")
load(":sanitizer_libs.bzl", "setup_sanitizer_libs")

def _single_setup_tag(module_ctx, ext_name, repos, attrs):
    tags = [
        tag
        for mod in module_ctx.modules
        for tag in mod.tags.setup
    ]
    if not tags:
        return None
    chosen = tags[0]
    for tag in tags[1:]:
        for attr_name in attrs:
            if getattr(tag, attr_name) == getattr(chosen, attr_name):
                continue
            fail(
                ("Conflicting setup() calls found for %s. " +
                 "Repository names are fixed to %s, so all modules " +
                 "must request identical configuration " +
                 "(differing attribute: %s).") % (ext_name, repos, attr_name),
            )
    return chosen

def _sanitizer_libs_impl(module_ctx):
    """Implementation of the sanitizer_libs module extension.

    This extension allows configuring sanitizer libraries in MODULE.bazel using
    the same setup_sanitizer_libs() function used in WORKSPACE.
    """

    # Collect all setup tags from all modules; multiple identical tags are
    # collapsed into one — only conflicting configurations are rejected.
    setup_tag = _single_setup_tag(
        module_ctx,
        "sanitizer_extension",
        "@msan_libs, @tsan_libs",
        ["msan_version", "msan_sha256", "tsan_version", "tsan_sha256"],
    )

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

    # Collect all setup tags from all modules; multiple identical tags are
    # collapsed into one — only conflicting configurations are rejected.
    setup_tag = _single_setup_tag(
        module_ctx,
        "libcxx_libs_extension",
        "@libcxx_libs_aarch64, @libcxx_libs_x86_64",
        ["aarch64_version", "aarch64_sha256", "x86_64_version", "x86_64_sha256"],
    )

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
    setup_llvm_prebuilt()

libcxx_extension = module_extension(
    implementation = _libcxx_ext_impl,
)

# =============================================================================
# llvm_minimal_extension: sets up released llvm_minimal_* repos used by
# consumers and host-tool aliases.
# =============================================================================

def _llvm_minimal_ext_impl(module_ctx):
    """Set up llvm_minimal_* repos for consumers."""
    # Collect all setup tags from all modules; multiple identical tags are
    # collapsed into one — only conflicting configurations are rejected.
    setup_tag = _single_setup_tag(
        module_ctx,
        "llvm_minimal_extension",
        "@llvm_minimal_linux_x64, @llvm_minimal_linux_arm64, @llvm_minimal_macos_arm64",
        ["linux_x64_sha256", "linux_arm64_sha256", "macos_arm64_sha256"],
    )

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
    """Set up the host-arch llvm_toolchain_llvm alias repo.

    This extension creates the llvm_minimal_* repos itself so they are siblings
    of the alias repo in a single visibility namespace, then passes them to the
    alias repo rule as apparent-name string labels. Because the minimal repos
    are created by THIS extension, they are visible by apparent name within the
    extension's repo mapping, so the strings resolve to canonical labels on the
    alias repo's attributes. Passing Label() objects instead would resolve
    against extensions.bzl's own repo mapping (which has no apparent-name entry
    for the extension-created repos) and fail in an external consumer's build.
    """
    setup_llvm_minimal()
    llvm_toolchain_alias(
        name = "llvm_toolchain_llvm",
        minimal_linux_x64 = "@llvm_minimal_linux_x64//:BUILD.bazel",
        minimal_linux_arm64 = "@llvm_minimal_linux_arm64//:BUILD.bazel",
        minimal_macos_arm64 = "@llvm_minimal_macos_arm64//:BUILD.bazel",
    )

llvm_toolchain_alias_extension = module_extension(
    implementation = _llvm_toolchain_alias_ext_impl,
)
