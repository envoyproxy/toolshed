"""Module extension for wee8 prebuilt repositories."""

load(":wee8_prebuilt.bzl", "setup_wee8_prebuilt")

def _single_setup_tag(module_ctx, repos, attrs):
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
                ("Conflicting setup() calls found for wee8_prebuilt_extension. " +
                 "Repository names are fixed to %s, so all modules must " +
                 "request identical configuration (differing attribute: %s).") % (
                    repos,
                    attr_name,
                ),
            )
    return chosen

def _wee8_prebuilt_ext_impl(module_ctx):
    setup_tag = _single_setup_tag(
        module_ctx,
        "@wee8_prebuilt_x86_64, @wee8_prebuilt_x86_64_libstdcxx, @wee8_prebuilt_aarch64",
        [
            "x86_64_version",
            "x86_64_sha256",
            "x86_64_libstdcxx_version",
            "x86_64_libstdcxx_sha256",
            "aarch64_version",
            "aarch64_sha256",
        ],
    )

    if setup_tag:
        setup_wee8_prebuilt(
            x86_64_version = setup_tag.x86_64_version,
            x86_64_sha256 = setup_tag.x86_64_sha256,
            x86_64_libstdcxx_version = setup_tag.x86_64_libstdcxx_version,
            x86_64_libstdcxx_sha256 = setup_tag.x86_64_libstdcxx_sha256,
            aarch64_version = setup_tag.aarch64_version,
            aarch64_sha256 = setup_tag.aarch64_sha256,
        )
    else:
        setup_wee8_prebuilt()

_setup = tag_class(
    attrs = {
        "x86_64_version": attr.string(
            doc = "Version of the x86_64 libcxx wee8 release to use",
        ),
        "x86_64_sha256": attr.string(
            doc = "SHA256 of the x86_64 libcxx wee8 archive",
        ),
        "x86_64_libstdcxx_version": attr.string(
            doc = "Version of the x86_64 libstdcxx wee8 release to use",
        ),
        "x86_64_libstdcxx_sha256": attr.string(
            doc = "SHA256 of the x86_64 libstdcxx wee8 archive",
        ),
        "aarch64_version": attr.string(
            doc = "Version of the aarch64 libcxx wee8 release to use",
        ),
        "aarch64_sha256": attr.string(
            doc = "SHA256 of the aarch64 libcxx wee8 archive",
        ),
    },
)

wee8_prebuilt_extension = module_extension(
    implementation = _wee8_prebuilt_ext_impl,
    tag_classes = {
        "setup": _setup,
    },
)
