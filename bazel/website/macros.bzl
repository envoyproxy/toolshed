load("@rules_pkg//pkg:mappings.bzl", "pkg_filegroup", "pkg_files")
load("@rules_pkg//pkg:pkg.bzl", "pkg_tar")

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
        decompressor_args = None,
        generator = "@envoy_toolshed//website/tools/pelican",
        extension = "tar.gz",
        output_path = "output",
        srcs = None,
        visibility = ["//visibility:public"],
):
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

    tools = [
        generator,
        name_sources,
    ] + sources

    if compressor:
        expand = "$(location %s) %s $(location %s) | tar x" % (
            compressor,
            decompressor_args or "",
            name_sources)
        tools += [compressor]
    else:
        expand = "tar xf $(location %s)" % name_sources

    native.genrule(
        name = name_website,
        cmd = """
        %s \
        && mkdir -p theme/static/css theme/static/images theme/static/js \
        && if [ -e theme/css ]; then cp -a theme/css/* theme/static/css; fi \
        && if [ -e theme/js ]; then cp -a theme/js/* theme/static/js; fi \
        && if [ -e theme/images ]; then cp -a theme/images/* theme/static/images; fi \
        && if [ -e theme/templates/extra ]; then cp -a theme/templates/extra/* theme/templates; fi \
        && $(location %s) %s \
        && tar cfh $@ --exclude=external -C %s .
        """ % (expand, generator, content_path, output_path),
        outs = [name_website_tarball],
        tools = tools
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
        visibility = ["//visibility:public"],
):

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
