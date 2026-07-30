# Quick Start: Provider-Based Website Builder

## What Changed?

The Bazel website builder now supports a provider-based architecture that allows different static site generators (Pelican, Sphinx, Yew/Rust, etc.) to be used interchangeably.

## For Existing Users

**No changes needed!** All existing code continues to work:

```starlark
# This still works exactly as before
static_website(
    name = "my_site",
    content = ":content",
    theme = ":theme",
    config = ":config.py",
    # Uses default Pelican generator
)
```

## For New Features

### Using Typed Assets

```starlark
load("//website/content:markdown.bzl", "markdown_assets")

markdown_assets(
    name = "blog_posts",
    srcs = glob(["content/**/*.md"]),
    prefix = "content",
)

static_website(
    name = "blog",
    content = ":blog_posts",  # Uses typed assets
    ...
)
```

### Using Custom Generators

```starlark
load("//website/generators:mock.bzl", "mock_generator")

mock_generator(
    name = "test_gen",
    accepts = ["markdown", "css", "js"],
)

static_website(
    name = "test_site",
    generator = ":test_gen",  # Custom generator
    ...
)
```

### Skeleton Generators (Extensibility Proof)

```starlark
# Sphinx for RST-based documentation
load("//website/generators:sphinx.bzl", "sphinx_generator")

sphinx_generator(name = "sphinx")

# Yew for Rust/WASM applications
load("//website/generators:yew.bzl", "yew_generator")

yew_generator(name = "yew")
```

## Documentation

- **PROVIDERS.md**: Complete architecture documentation
- **EXAMPLES.md**: Detailed usage examples
- **IMPLEMENTATION.md**: Implementation summary

## Testing

```bash
cd bazel
bazel test //website/tests/...
```

All tests pass:
- ✅ provider_architecture_test (new)
- ✅ website_generation_test (existing)
- ✅ website_parameterized_test (existing)
- ✅ website_compression_test (existing)

## Adding Your Own Generator

1. Create a generator rule that produces `WebsiteGeneratorInfo`
2. Declare what asset types it accepts
3. Use it with `static_website`

See **PROVIDERS.md** for detailed instructions.

## Benefits

- 🔌 **Extensible**: Support any static site generator
- ♻️ **Backwards Compatible**: All existing code works unchanged
- 🧪 **Tested**: Comprehensive test suite validates all functionality
- 📚 **Documented**: Complete documentation with examples
- 🚀 **Ready**: Skeleton generators prove viability of new types

## Support

For questions or issues, refer to:
- Architecture: `PROVIDERS.md`
- Examples: `EXAMPLES.md`
- Implementation: `IMPLEMENTATION.md`
