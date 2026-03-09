"""Module extension for cross-compilation libc++ libraries configuration in bzlmod."""

load(":libcxx_cross.bzl", "setup_libcxx_cross")

def _libcxx_cross_extension_impl(module_ctx):
    """Implementation of the libcxx_cross module extension.

    This extension allows configuring cross-compilation libc++ libraries in
    MODULE.bazel using the same setup_libcxx_cross() function used in WORKSPACE.
    Multiple setup() calls are allowed, one per target architecture.
    """
    seen_arches = []
    for mod in module_ctx.modules:
        for tag in mod.tags.setup:
            arch = tag.target_arch
            if arch in seen_arches:
                fail("Duplicate setup() call for arch '{}' in libcxx_cross_extension. Each architecture can only be configured once.".format(arch))
            seen_arches.append(arch)
            setup_libcxx_cross(
                target_arch = arch,
                version = tag.version,
                sha256 = tag.sha256,
            )

_setup = tag_class(
    attrs = {
        "target_arch": attr.string(
            mandatory = True,
            doc = "Target architecture (e.g., 'aarch64', 'x86_64')",
        ),
        "version": attr.string(
            doc = "Toolshed bins release version (default: VERSIONS['bins_release'] from //:versions.bzl)",
        ),
        "sha256": attr.string(
            doc = "SHA256 hash of the published cross libs tarball (default: VERSIONS['libcxx_cross_sha256'][target_arch] from //:versions.bzl)",
        ),
    },
)

libcxx_cross_extension = module_extension(
    implementation = _libcxx_cross_extension_impl,
    tag_classes = {
        "setup": _setup,
    },
)
