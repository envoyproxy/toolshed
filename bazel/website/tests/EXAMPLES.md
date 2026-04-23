# Provider Architecture Examples

This directory demonstrates how to use the new provider-based website builder architecture.

## Basic Examples

### Example 1: Using Typed Asset Rules

```starlark
load("//website/content:markdown.bzl", "markdown_assets")
load("//website/templates:jinja.bzl", "jinja_templates")

# Create markdown content assets
markdown_assets(
    name = "blog_content",
    srcs = glob(["content/blog/**/*.md"]),
    prefix = "content/blog",
)

# Create Jinja2 templates
jinja_templates(
    name = "blog_templates",
    srcs = glob(["templates/**/*.html"]),
    prefix = "theme/templates",
)
```

### Example 2: Using Custom Generators

```starlark
load("//website/generators:mock.bzl", "mock_generator")
load("//website:macros.bzl", "static_website")

# Create a mock generator for testing
mock_generator(
    name = "test_gen",
    accepts = ["markdown", "jinja", "css", "js", "static"],
    output_path = "output",
)

# Use it to build a site
static_website(
    name = "test_site",
    content = ":blog_content",
    theme = ":blog_templates",
    config = ":config.py",
    generator = ":test_gen",
)
```

### Example 3: Skeleton Generators for Extensibility

The framework includes skeleton generators that prove different generator types work:

```starlark
load("//website/generators:sphinx.bzl", "sphinx_generator")
load("//website/generators:yew.bzl", "yew_generator")
load("//website/content:rst.bzl", "rst_assets")

# Sphinx generator for RST-based sites
sphinx_generator(
    name = "sphinx",
    accepts = ["rst", "markdown", "sphinx_theme", "css", "js", "static"],
)

rst_assets(
    name = "docs",
    srcs = glob(["docs/**/*.rst"]),
    prefix = "docs",
)

static_website(
    name = "sphinx_site",
    content = ":docs",
    generator = ":sphinx",
)

# Yew generator for Rust/WASM sites
yew_generator(
    name = "yew",
    accepts = ["rust_component", "css", "js", "static", "wasm"],
)

static_website(
    name = "wasm_site",
    content = ":components",
    generator = ":yew",
)
```

## Real Examples in Tests

See the actual working examples in `BUILD`:

- `test_mock_markdown`: Mock generator with markdown assets
- `test_sphinx_skeleton`: Sphinx generator skeleton
- `test_yew_skeleton`: Yew/WASM generator skeleton
- `test_mock_mixed`: Mixed asset types

## Asset Type Reference

Common asset types:

- `markdown`: Markdown content files
- `rst`: reStructuredText files
- `jinja`: Jinja2 templates
- `rst_template`: RST templates (for Sphinx)
- `scss`: SCSS stylesheets
- `css`: CSS stylesheets
- `js`: JavaScript files
- `static`: Generic static files
- `rust_component`: Rust source files (for Yew)
- `wasm`: WebAssembly modules
- `sphinx_theme`: Sphinx theme files

## Generator Type Reference

Available generators:

- **Pelican** (`//website/generators:pelican.bzl`): Production-ready Pelican generator
- **Mock** (`//website/generators:mock.bzl`): Testing generator
- **Sphinx** (`//website/generators:sphinx.bzl`): Skeleton for RST-based sites
- **Yew** (`//website/generators:yew.bzl`): Skeleton for Rust/WASM sites

## Creating Custom Generators

See `PROVIDERS.md` for detailed documentation on creating custom generators.
