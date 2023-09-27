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
