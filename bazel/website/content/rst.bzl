"""reStructuredText content asset rules."""

load("//website:assets.bzl", "static_assets")

def rst_assets(
        name,
        srcs = None,
        deps = None,
        prefix = "content",
        **kwargs):
    """Create reStructuredText content assets.
    
    Args:
        name: Name of the target
        srcs: RST files
        deps: Dependencies
        prefix: Mount point (default: "content")
        **kwargs: Additional arguments
    """
    static_assets(
        name = name,
        srcs = srcs,
        deps = deps,
        asset_type = "rst",
        prefix = prefix,
        **kwargs
    )
