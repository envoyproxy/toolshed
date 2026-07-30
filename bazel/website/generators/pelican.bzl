"""Pelican generator with WebsiteGeneratorInfo provider."""

load("//website:providers.bzl", "WebsiteGeneratorInfo")

def _pelican_generator_impl(ctx):
    """Implementation for pelican generator wrapper."""
    # Get the actual pelican executable
    pelican_executable = ctx.executable.pelican
    
    # Create a wrapper script that provides the generator interface
    wrapper = ctx.actions.declare_file(ctx.label.name + "_wrapper.sh")
    
    ctx.actions.write(
        output = wrapper,
        content = """#!/bin/bash
set -e

CONTENT_PATH="$1"
PELICAN_BIN="{pelican}"

# Run pelican
$PELICAN_BIN "$CONTENT_PATH"
""".format(
            pelican = pelican_executable.path,
        ),
        is_executable = True,
    )
    
    # Create WebsiteGeneratorInfo provider
    generator_info = WebsiteGeneratorInfo(
        executable = wrapper,
        accepts = ctx.attr.accepts,
        output_path = ctx.attr.output_path,
        dev_server = None,
    )
    
    # Collect runfiles from pelican
    runfiles = ctx.runfiles(files = [wrapper, pelican_executable])
    runfiles = runfiles.merge(ctx.attr.pelican[DefaultInfo].default_runfiles)
    
    return [
        generator_info,
        DefaultInfo(
            executable = wrapper,
            runfiles = runfiles,
        ),
    ]

pelican_generator = rule(
    implementation = _pelican_generator_impl,
    attrs = {
        "pelican": attr.label(
            mandatory = True,
            executable = True,
            cfg = "exec",
            doc = "The pelican executable",
        ),
        "accepts": attr.string_list(
            default = ["markdown", "rst", "jinja", "scss", "css", "js", "static"],
            doc = "List of asset types this generator accepts",
        ),
        "output_path": attr.string(
            default = "output",
            doc = "Where the generator puts output",
        ),
    },
    executable = True,
    doc = "Pelican generator with WebsiteGeneratorInfo provider",
)
