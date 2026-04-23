"""Markdown content asset rules."""

load("//website:assets.bzl", "static_assets")

def markdown_assets(
        name,
        srcs = None,
        deps = None,
        prefix = "content",
        **kwargs):
    """Create markdown content assets.
    
    Args:
        name: Name of the target
        srcs: Markdown files
        deps: Dependencies
        prefix: Mount point (default: "content")
        **kwargs: Additional arguments
    """
    static_assets(
        name = name,
        srcs = srcs,
        deps = deps,
        asset_type = "markdown",
        prefix = prefix,
        **kwargs
    )
