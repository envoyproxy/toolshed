"""Module extension for glint configuration in bzlmod."""

load(":glint_repository.bzl", "glint_repository")

def _glint_impl(module_ctx):
    """Implementation of the glint module extension.

    This extension allows configuring glint in MODULE.bazel using the same
    glint_repository() function used when loading the file directly.
    """

    # Collect all setup tags from all modules
    # Only use the first tag found (glint repo has a fixed name)
    setup_tag = None
    for mod in module_ctx.modules:
        for tag in mod.tags.setup:
            if setup_tag == None:
                setup_tag = tag
            else:
                # Fail if multiple tags are found
                fail("Multiple setup() calls found for glint_extension. Only one configuration is allowed since repository name is fixed to @glint.")

    if setup_tag == None:
        fail("glint_extension requires a setup() call with bins_release_version set.")

    glint_repository(bins_release_version = setup_tag.bins_release_version)

_setup = tag_class(
    attrs = {
        "bins_release_version": attr.string(
            doc = "Version of bins release to use",
            mandatory = True,
        ),
    },
)

glint_extension = module_extension(
    implementation = _glint_impl,
    tag_classes = {
        "setup": _setup,
    },
)
