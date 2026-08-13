"""Module extension for wee8 prebuilt configuration in bzlmod."""

load(":wee8_prebuilt.bzl", "setup_wee8_prebuilt")

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

def _wee8_ext_impl(module_ctx):
    setup_tag = _single_setup_tag(
        module_ctx,
        "wee8_extension",
        "@wee8_prebuilt_x86_64, @wee8_prebuilt_aarch64",
        ["x86_64_version", "x86_64_sha256", "aarch64_version", "aarch64_sha256"],
    )

    if setup_tag:
        setup_wee8_prebuilt(
            x86_64_version = setup_tag.x86_64_version or None,
            x86_64_sha256 = setup_tag.x86_64_sha256 or None,
            aarch64_version = setup_tag.aarch64_version or None,
            aarch64_sha256 = setup_tag.aarch64_sha256 or None,
        )
    else:
        setup_wee8_prebuilt()

_setup = tag_class(
    attrs = {
        "x86_64_version": attr.string(
            doc = "Version of x86_64 wee8 release to use (default: VERSIONS['bins_release'] from //:versions.bzl)",
        ),
        "x86_64_sha256": attr.string(
            doc = "SHA256 hash of the x86_64 wee8 archive (default: VERSIONS['wee8_sha256']['x86_64'] from //:versions.bzl)",
        ),
        "aarch64_version": attr.string(
            doc = "Version of aarch64 wee8 release to use (default: VERSIONS['bins_release'] from //:versions.bzl)",
        ),
        "aarch64_sha256": attr.string(
            doc = "SHA256 hash of the aarch64 wee8 archive (default: VERSIONS['wee8_sha256']['aarch64'] from //:versions.bzl)",
        ),
    },
)

wee8_extension = module_extension(
    implementation = _wee8_ext_impl,
    tag_classes = {
        "setup": _setup,
    },
)
