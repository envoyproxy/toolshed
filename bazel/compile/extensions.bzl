"""Module extension for sanitizer libraries configuration in bzlmod."""

load(":libcxx_cross.bzl", "setup_libcxx_cross")
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

def _libcxx_cross_extension_impl(module_ctx):
    """Implementation of the libcxx_cross module extension.

    This extension allows configuring cross-compilation libc++ libraries in
    MODULE.bazel using the same setup_libcxx_cross() function used in WORKSPACE.
    """

    # Collect all setup tags from all modules
    # Only use the first tag found (repo has a fixed name)
    setup_tag = None
    for mod in module_ctx.modules:
        for tag in mod.tags.setup:
            if setup_tag == None:
                setup_tag = tag
            else:
                # Fail if multiple tags are found
                fail("Multiple setup() calls found for libcxx_cross_extension. Only one configuration is allowed since repository name is fixed to @libcxx_cross.")

    # Call setup_libcxx_cross once with the configuration
    if setup_tag:
        setup_libcxx_cross(
            target_arch = setup_tag.target_arch,
            llvm_version = setup_tag.llvm_version,
            sha256 = setup_tag.sha256,
        )
    else:
        # Use default configuration if no tags specified
        setup_libcxx_cross()

_libcxx_cross_setup = tag_class(
    attrs = {
        "target_arch": attr.string(
            doc = "Target architecture (default: 'aarch64')",
        ),
        "llvm_version": attr.string(
            doc = "LLVM version to download (default: VERSIONS['llvm'] from //:versions.bzl)",
        ),
        "sha256": attr.string(
            doc = "SHA256 hash of the LLVM release tarball (default: VERSIONS['libcxx_cross_sha256'][target_arch] from //:versions.bzl)",
        ),
    },
)

libcxx_cross_extension = module_extension(
    implementation = _libcxx_cross_extension_impl,
    tag_classes = {
        "setup": _libcxx_cross_setup,
    },
)
