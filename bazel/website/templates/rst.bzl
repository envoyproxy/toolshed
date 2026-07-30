"""reStructuredText template asset rules."""

load("//website:assets.bzl", "static_assets")

def rst_templates(
        name,
        srcs = None,
        deps = None,
        prefix = "theme/templates",
        **kwargs):
    """Create reStructuredText template assets (for Sphinx).
    
    Args:
        name: Name of the target
        srcs: RST template files
        deps: Dependencies
        prefix: Mount point (default: "theme/templates")
        **kwargs: Additional arguments
    """
    static_assets(
        name = name,
        srcs = srcs,
        deps = deps,
        asset_type = "rst_template",
        prefix = prefix,
        **kwargs
    )
