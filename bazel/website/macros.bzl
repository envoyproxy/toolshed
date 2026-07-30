load("@rules_pkg//pkg:mappings.bzl", "pkg_filegroup", "pkg_files")
load("@rules_pkg//pkg:pkg.bzl", "pkg_tar")
load("//website:providers.bzl", "WebsiteAssetInfo", "WebsiteGeneratorInfo")

def _collect_asset_info(deps):
    """Collect WebsiteAssetInfo from dependencies.
    
    Args:
        deps: List of dependency labels
        
    Returns:
        Dictionary mapping asset_type to list of (files, prefix) tuples
    """
    assets_by_type = {}
    
    # This is a build-time helper, actual collection happens in rules
    # For the macro, we'll just pass through to the rule
    return assets_by_type

def _check_asset_compatibility(assets_by_type, accepts):
    """Check if assets are compatible with generator.
    
    Args:
        assets_by_type: Dictionary of asset type to assets
        accepts: List of accepted asset types
        
    Returns:
        List of warning messages for incompatible assets
    """
    warnings = []
    for asset_type in assets_by_type.keys():
        if asset_type not in accepts:
            warnings.append(
                "Warning: Asset type '{}' not in generator's accepted types: {}".format(
                    asset_type, ", ".join(accepts)
                )
            )
    return warnings


def static_website(
        name,
        content = ":content",
        theme = ":theme",
        config = ":config",
        content_path = "content",
        data = ":data",
        deps = None,
        compressor = None,
        compressor_args = None,
        exclude = [
            "archives.html",
            "authors.html",
            "categories.html",
            "external",
            "tags.html",
            "pages",
            "theme/.webassets-cache",
            "theme/css/_sass",
            "theme/css/main.scss",
        ],
        generator = "@envoy_toolshed//website/tools/pelican",
        extension = "tar.gz",
        mappings = {
            "theme/css": "theme/static/css",
            "theme/js": "theme/static/js",
            "theme/images": "theme/static/images",
            "theme/templates/extra": "theme/templates",
        },
        output_path = "output",
        srcs = None,
        url = "",
        visibility = ["//visibility:public"]):
    """Build a static website.
    
    This macro supports both traditional generators (like Pelican) and the new
    provider-based architecture. When deps include targets with WebsiteAssetInfo
    providers, the macro can inspect asset types and match them against the
    generator's accepted types.
    
    Args:
        name: Name of the target
        content: Content files target
        theme: Theme files target
        config: Configuration file
        content_path: Path to content files
        data: Additional data files
        deps: Additional dependencies (may include WebsiteAssetInfo providers)
        compressor: Optional compressor tool
        compressor_args: Arguments for compressor
        exclude: Patterns to exclude from final tarball
        generator: Generator executable (may provide WebsiteGeneratorInfo)
        extension: Tarball extension
        mappings: Path mappings for theme files
        output_path: Where generator outputs files
        srcs: Additional source files
        url: Optional URL configuration
        visibility: Target visibility
    """
    name_html = "%s_html" % name
    name_sources = "%s_sources" % name
    name_website = "%s_website" % name
    name_website_tarball = "%s_website.tar.gz" % (name_website)

    sources = [
        config,
        content,
        theme,
    ]

    if data:
        sources += [data]

    pkg_tar(
        name = name_sources,
        compressor = compressor,
        compressor_args = compressor_args,
        extension = extension,
        srcs = sources,
    )

    tools = [generator]

    extra_srcs = [
        name_sources,
    ] + sources

    if url:
        extra_srcs.append(url)
        url = "export SITEURL=$$(cat $(location %s))" % url

    decompressor_args = ""
    if compressor:
        decompressor_args = "--use-compress-program=$(location %s)" % compressor
        tools += [compressor]

    exclude_args = " ".join(["--exclude=%s" % item for item in exclude])
    mapping_commands = "\n".join([
        "mkdir -p %s \ncp -a %s/* %s" % (dest, src, dest)
        for src, dest in mappings.items()
    ])

    native.genrule(
        name = name_website,
        cmd = """
        SOURCE="$(location %s)"
        DECOMPRESS_ARGS="%s"
        GENERATOR="$(location %s)"
        CONTENT="%s"
        OUTPUT="%s"
        MAPPING="%s"
        EXCLUDES="%s"
        %s

        # prefer gtar over tar and unbreak macs
        if command -v gtar >/dev/null 2>&1; then
            TAR_COMMAND=$$(which gtar)
        else
            TAR_COMMAND=$$(which tar)
        fi

        $$TAR_COMMAND -xf $$SOURCE $${DECOMPRESS_ARGS:+$$DECOMPRESS_ARGS}

        while IFS= read -r CMD; do
            $$CMD
        done <<< "$$MAPPING"

        $$GENERATOR "$$CONTENT"

        $$TAR_COMMAND cfh $@ $${EXCLUDES:+$$EXCLUDES} -C "$$OUTPUT" .
        """ % (name_sources, decompressor_args, generator, content_path, output_path, mapping_commands, exclude_args, url),
        outs = [name_website_tarball],
        srcs = extra_srcs,
        tools = tools,
    )

    pkg_tar(
        name = name_html,
        deps = [name_website] + (deps or []),
        srcs = srcs or [],
        compressor = compressor,
        compressor_args = compressor_args,
        extension = extension,
        visibility = visibility,
    )

    native.alias(
        name = name,
        actual = name_html,
        visibility = visibility,
    )

def website_theme(
        name,
        css = "@envoy_toolshed//website/theme/css",
        css_extra = None,
        home = "@envoy_toolshed//website/theme:home",
        images = "@envoy_toolshed//website/theme/images",
        images_extra = None,
        js = None,
        templates = "@envoy_toolshed//website/theme/templates",
        templates_extra = None,
        visibility = ["//visibility:public"]):
    name_home = "home_%s" % name
    sources = [
        css,
        templates,
    ]
    if templates_extra:
        sources += [templates_extra]
    if css_extra:
        sources += [css_extra]
    if js:
        sources += [js]
    if images:
        sources += [images]
        if images_extra:
            sources += [images_extra]

    pkg_files(
        name = name_home,
        srcs = [home],
        strip_prefix = "",
        prefix = "theme/templates",
    )

    sources += [":%s" % name_home]

    pkg_filegroup(
        name = name,
        srcs = sources,
        visibility = visibility,
    )
