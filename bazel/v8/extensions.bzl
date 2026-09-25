"""Module extension for wee8 prebuilt repositories."""

load(":wee8_prebuilt.bzl", "setup_wee8_prebuilt", "wee8_source_repo")

_SHA_ATTRS = [
    "x86_64_version",
    "x86_64_sha256",
    "x86_64_libstdcxx_version",
    "x86_64_libstdcxx_sha256",
    "aarch64_version",
    "aarch64_sha256",
]

_REPOS = "@wee8_prebuilt_x86_64, @wee8_prebuilt_x86_64_libstdcxx, @wee8_prebuilt_aarch64"

def _module_id(mod):
    if mod.version:
        return "%s@%s" % (mod.name, mod.version)
    return mod.name

def _merge_sha_attrs(tags):
    """All set values for each sha/version attr must agree across tags."""
    merged = {}
    for module_id, tag in tags:
        for attr_name in _SHA_ATTRS:
            value = getattr(tag, attr_name)
            if not value:
                continue
            if attr_name in merged and merged[attr_name][1] != value:
                fail(
                    ("Conflicting setup() calls found for wee8_prebuilt_extension. " +
                     "Repository names are fixed to %s, so all modules must request " +
                     "identical configuration (attribute %s: %s from %s vs %s from %s).") % (
                        _REPOS,
                        attr_name,
                        merged[attr_name][1],
                        merged[attr_name][0],
                        value,
                        module_id,
                    ),
                )
            merged[attr_name] = (module_id, value)
    return {k: v[1] for k, v in merged.items()}

def _pick_source(tags):
    """Root module wins; then non-root. Differing set values at one tier fail."""
    chosen = None
    chosen_module = None
    for module_id, tag in tags:
        if tag.source == None:
            continue
        if chosen == None:
            chosen = tag.source
            chosen_module = module_id
        elif str(chosen) != str(tag.source):
            fail(
                "Conflicting wee8_prebuilt_extension.setup(source=...) labels from " +
                "modules %s (%s) and %s (%s)." % (chosen_module, chosen, module_id, tag.source),
            )
    return chosen

def _wee8_prebuilt_ext_impl(module_ctx):
    root_tags = []
    non_root_tags = []
    for mod in module_ctx.modules:
        for tag in mod.tags.setup:
            entry = (_module_id(mod), tag)
            if mod.is_root:
                root_tags.append(entry)
            else:
                non_root_tags.append(entry)

    setup_wee8_prebuilt(**_merge_sha_attrs(root_tags + non_root_tags))

    source = _pick_source(root_tags)
    if source == None:
        source = _pick_source(non_root_tags)
    wee8_source_repo(
        name = "wee8_source",
        actual = source,
    )

    return module_ctx.extension_metadata(reproducible = True)

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
        "source": attr.label(
            doc = "Target to build wee8 from source when no prebuilt matches the " +
                  "target platform (eg `@v8//:wee8`). Unset: //v8:wee8 is " +
                  "incompatible on those platforms.",
        ),
    },
)

wee8_prebuilt_extension = module_extension(
    implementation = _wee8_prebuilt_ext_impl,
    tag_classes = {
        "setup": _setup,
    },
)
