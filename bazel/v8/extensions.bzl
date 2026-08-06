"""Module extension for pre-built V8 library configuration in bzlmod."""

load(":v8_libs.bzl", "v8_prebuilt")

def _v8_libs_impl(module_ctx):
    """Implementation of the v8_libs module extension."""
    setup_tag = None
    for mod in module_ctx.modules:
        for tag in mod.tags.setup:
            if setup_tag == None:
                setup_tag = tag
            else:
                fail("Multiple setup() calls found for v8_extension. Only one configuration is allowed since the repository name is fixed to @v8.")

    if setup_tag:
        v8_prebuilt(
            name = "v8",
            version = setup_tag.version,
            sha256 = {
                "x86_64": setup_tag.sha256_x86_64,
                "aarch64": setup_tag.sha256_aarch64,
            },
        )

_setup = tag_class(
    attrs = {
        "version": attr.string(
            mandatory = True,
            doc = "V8 version to use",
        ),
        "sha256_x86_64": attr.string(
            doc = "SHA256 hash for x86_64 architecture",
        ),
        "sha256_aarch64": attr.string(
            doc = "SHA256 hash for aarch64 architecture",
        ),
    },
)

v8_extension = module_extension(
    implementation = _v8_libs_impl,
    tag_classes = {
        "setup": _setup,
    },
)
