"""Jinja2 template asset rules."""

load("//website:assets.bzl", "static_assets")

def jinja_templates(
        name,
        srcs = None,
        deps = None,
        prefix = "theme/templates",
        **kwargs):
    """Create Jinja2 template assets.
    
    Args:
        name: Name of the target
        srcs: Jinja2 template files (.html, .j2, etc)
        deps: Dependencies
        prefix: Mount point (default: "theme/templates")
        **kwargs: Additional arguments
    """
    static_assets(
        name = name,
        srcs = srcs,
        deps = deps,
        asset_type = "jinja",
        prefix = prefix,
        **kwargs
    )
