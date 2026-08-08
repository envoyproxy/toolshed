"""Base asset rules for the website builder framework."""

load("@rules_pkg//pkg:mappings.bzl", "pkg_files")
load("//website:providers.bzl", "WebsiteAssetInfo")

def _asset_impl(ctx):
    """Implementation for generic asset rules."""
    # Collect all files from srcs
    files = depset(
        direct = ctx.files.srcs,
        transitive = [dep[DefaultInfo].files for dep in ctx.attr.deps],
    )
    
    # Create WebsiteAssetInfo provider
    asset_info = WebsiteAssetInfo(
        files = files,
        asset_type = ctx.attr.asset_type,
        prefix = ctx.attr.prefix,
    )
    
    # Return both the new provider and DefaultInfo for backwards compatibility
    return [
        asset_info,
        DefaultInfo(files = files),
    ]

_asset_rule = rule(
    implementation = _asset_impl,
    attrs = {
        "srcs": attr.label_list(
            allow_files = True,
            doc = "Source files for this asset",
        ),
        "deps": attr.label_list(
            doc = "Dependencies that also provide assets",
            providers = [[DefaultInfo]],
        ),
        "asset_type": attr.string(
            mandatory = True,
            doc = "Type of asset (markdown, jinja, rst, scss, css, js, static, etc)",
        ),
        "prefix": attr.string(
            default = "",
            doc = "Mount point in source tree",
        ),
    },
    doc = "Generic rule for website assets that produces WebsiteAssetInfo",
)

def static_assets(
        name,
        srcs = None,
        deps = None,
        asset_type = "static",
        prefix = "",
        strip_prefix = None,
        visibility = None,
        **kwargs):
    """Create static assets with WebsiteAssetInfo.
    
    This is a convenience wrapper that creates both the typed asset rule
    and a pkg_files target for backwards compatibility.
    
    Args:
        name: Name of the target
        srcs: Source files
        deps: Dependencies
        asset_type: Type of asset (default: "static")
        prefix: Mount point in source tree
        strip_prefix: Strip prefix for pkg_files (backwards compat)
        visibility: Visibility
        **kwargs: Additional arguments passed to pkg_files
    """
    # Create the asset rule that produces WebsiteAssetInfo
    _asset_rule(
        name = "%s_asset" % name,
        srcs = srcs or [],
        deps = deps or [],
        asset_type = asset_type,
        prefix = prefix,
        visibility = visibility,
    )
    
    # Also create pkg_files for backwards compatibility
    pkg_files_kwargs = {
        "srcs": srcs or [],
        "prefix": prefix,
        "visibility": visibility,
    }
    
    if strip_prefix != None:
        pkg_files_kwargs["strip_prefix"] = strip_prefix
    
    # Merge any additional kwargs
    pkg_files_kwargs.update(kwargs)
    
    pkg_files(
        name = name,
        **pkg_files_kwargs
    )
