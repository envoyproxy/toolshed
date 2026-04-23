"""Providers for the website builder framework."""

WebsiteAssetInfo = provider(
    doc = """Provider for website assets with type information.
    
    This provider allows assets to declare what type they are (markdown, jinja, 
    rst, scss, static, rust_component, etc.) so that generators can selectively 
    consume the assets they understand.
    """,
    fields = {
        "files": "depset of files for this asset",
        "asset_type": "string identifier (markdown, jinja, rst, scss, css, js, static, rust_component, wasm, etc)",
        "prefix": "mount point in source tree (where these files should be placed)",
    },
)

WebsiteGeneratorInfo = provider(
    doc = """Provider for website generators.
    
    This provider declares what a generator can process and how to invoke it.
    """,
    fields = {
        "executable": "the build tool (File)",
        "accepts": "list of asset_types this generator handles",
        "output_path": "where it puts output (string)",
        "dev_server": "optional dev mode executable (File or None)",
    },
)
