"""Module extension for sanitizer libraries configuration in bzlmod."""

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
            if setup_tag is None:
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
