# Website Builder Provider Architecture

## Overview

The website builder framework now supports a provider-based architecture that makes it extensible to different static site generators (Pelican, Sphinx, Yew/Rust, etc).

## Architecture

### Providers (`bazel/website/providers.bzl`)

Two providers enable the extensible architecture:

#### WebsiteAssetInfo

Declares what type of asset a target provides:

```starlark
WebsiteAssetInfo(
    files = depset(...),           # Files for this asset
    asset_type = "markdown",       # Type: markdown, rst, jinja, css, js, static, etc.
    prefix = "content",            # Where to mount in source tree
)
```

#### WebsiteGeneratorInfo

Declares what a generator can process:

```starlark
WebsiteGeneratorInfo(
    executable = script_file,      # The generator tool
    accepts = ["markdown", "rst"], # Asset types it can handle
    output_path = "output",        # Where it outputs files
    dev_server = None,             # Optional dev server
)
```

### Asset Rules

Typed asset rules produce `WebsiteAssetInfo` with the appropriate `asset_type`:

- **Content**: `markdown_assets`, `rst_assets` (in `bazel/website/content/`)
- **Templates**: `jinja_templates`, `rst_templates` (in `bazel/website/templates/`)
- **Generic**: `static_assets` (in `bazel/website/assets.bzl`)

Example:

```starlark
load("//website/content:markdown.bzl", "markdown_assets")

markdown_assets(
    name = "my_content",
    srcs = glob(["content/**/*.md"]),
    prefix = "content",
)
```

### Generator Rules

Generator rules produce `WebsiteGeneratorInfo` and declare what they accept:

#### Pelican (`bazel/website/generators/pelican.bzl`)

```starlark
load("//website/generators:pelican.bzl", "pelican_generator")

pelican_generator(
    name = "my_pelican",
    pelican = "//website/tools/pelican",
    accepts = ["markdown", "rst", "jinja", "scss", "css", "js", "static"],
    output_path = "output",
)
```

#### Mock Generator (for testing)

```starlark
load("//website/generators:mock.bzl", "mock_generator")

mock_generator(
    name = "test_gen",
    accepts = ["markdown", "rst"],
    output_path = "output",
)
```

#### Skeleton Generators

- **Sphinx** (`bazel/website/generators/sphinx.bzl`): Proves RST-based generators work
- **Yew** (`bazel/website/generators/yew.bzl`): Proves Rust/WASM generators work

### Using Providers with static_website

The `static_website` macro in `bazel/website/macros.bzl` now supports provider-based generators:

```starlark
load("//website:macros.bzl", "static_website")
load("//website/content:markdown.bzl", "markdown_assets")
load("//website/generators:mock.bzl", "mock_generator")

markdown_assets(
    name = "content",
    srcs = glob(["content/**/*.md"]),
)

mock_generator(
    name = "gen",
    accepts = ["markdown", "css", "js"],
)

static_website(
    name = "my_site",
    content = ":content",
    generator = ":gen",
    ...
)
```

## Backwards Compatibility

The new architecture maintains full backwards compatibility:

1. **Existing `static_website` calls work unchanged**
   - The macro still accepts traditional Pelican generators
   - All parameters have the same defaults
   - Old-style content/theme targets work as before

2. **Asset rules produce both providers AND pkg_files**
   - `WebsiteAssetInfo` for new functionality
   - Traditional `pkg_files` output for existing workflows

3. **All existing tests pass**
   - Tests in `bazel/website/tests/` validate backwards compatibility

## Testing

### Existing Tests

All original tests continue to pass:
- `website_generation_test`: Basic Pelican generation
- `website_parameterized_test`: Custom configurations
- `website_compression_test`: Compression support

### New Provider Tests

New `provider_architecture_test` validates:
- `WebsiteAssetInfo` attachment by asset rules
- `WebsiteGeneratorInfo` attachment by generator rules
- Mock generator handles correct asset types
- Sphinx skeleton proves RST generator viability
- Yew skeleton proves Rust/WASM generator viability
- Mixed asset types route correctly

Run tests:

```bash
cd bazel
bazel test //website/tests/...
```

## Extensibility

The framework now supports adding new generators:

### Adding a New Generator (Example: Hugo)

1. Create `bazel/website/generators/hugo.bzl`:

```starlark
load("//website:providers.bzl", "WebsiteGeneratorInfo")

def _hugo_generator_impl(ctx):
    # Create wrapper script
    script = ctx.actions.declare_file(ctx.label.name + ".sh")
    ctx.actions.write(
        output = script,
        content = "#!/bin/bash\nhugo ...",
        is_executable = True,
    )
    
    return [
        WebsiteGeneratorInfo(
            executable = script,
            accepts = ["markdown", "hugo_template", "css", "js", "static"],
            output_path = "public",
        ),
        DefaultInfo(executable = script, ...),
    ]

hugo_generator = rule(
    implementation = _hugo_generator_impl,
    ...
)
```

2. Use it:

```starlark
load("//website/generators:hugo.bzl", "hugo_generator")

hugo_generator(name = "hugo")

static_website(
    name = "site",
    generator = ":hugo",
    ...
)
```

### Adding Custom Asset Types

Create new asset rules that produce `WebsiteAssetInfo` with custom `asset_type` values:

```starlark
load("//website:assets.bzl", "static_assets")

def toml_config(name, srcs, **kwargs):
    static_assets(
        name = name,
        srcs = srcs,
        asset_type = "toml_config",
        prefix = "config",
        **kwargs
    )
```

## Directory Structure

```
bazel/website/
├── providers.bzl           # WebsiteAssetInfo, WebsiteGeneratorInfo
├── assets.bzl              # Base asset rule, static_assets
├── macros.bzl              # static_website, website_theme (backwards compat)
├── content/
│   ├── BUILD
│   ├── markdown.bzl        # markdown_assets
│   └── rst.bzl             # rst_assets
├── templates/
│   ├── BUILD
│   ├── jinja.bzl           # jinja_templates
│   └── rst.bzl             # rst_templates
├── generators/
│   ├── BUILD
│   ├── pelican.bzl         # Pelican with WebsiteGeneratorInfo
│   ├── mock.bzl            # Mock generator for testing
│   ├── sphinx.bzl          # Sphinx skeleton
│   └── yew.bzl             # Yew/Rust skeleton
└── tests/                  # All tests
```

## Migration Guide

### For Existing Users

No migration needed! All existing code continues to work.

### For New Generators

To add support for a new generator:

1. Create a generator rule that produces `WebsiteGeneratorInfo`
2. Declare what `asset_type` values it accepts
3. Use it with `static_website`

### For Custom Assets

To add new asset types:

1. Use `static_assets` with a custom `asset_type`
2. Or create a wrapper macro for convenience
3. Use with generators that accept that type
