"""Module extension providing the prebuilt `lcov-merge` binary."""

load(":lcov_merge_repository.bzl", "lcov_merge_repository")

def _lcov_merge_impl(module_ctx):
    setup_tag = None
    for mod in module_ctx.modules:
        for tag in mod.tags.setup:
            if setup_tag == None:
                setup_tag = tag
            else:
                fail("Multiple setup() calls found for lcov_merge_extension. Only one configuration is allowed since the repository name is fixed to @lcov_merge.")
    if setup_tag == None:
        fail("lcov_merge_extension requires a setup() call with bins_release_version set.")
    lcov_merge_repository(bins_release_version = setup_tag.bins_release_version)

_setup = tag_class(
    attrs = {
        "bins_release_version": attr.string(
            doc = "Version of the toolshed bins release to download lcov-merge from",
            mandatory = True,
        ),
    },
)

lcov_merge_extension = module_extension(
    implementation = _lcov_merge_impl,
    tag_classes = {"setup": _setup},
)
