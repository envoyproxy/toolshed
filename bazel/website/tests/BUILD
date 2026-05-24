load("@rules_pkg//pkg:mappings.bzl", "pkg_filegroup", "pkg_files")
load("@rules_shell//shell:sh_test.bzl", "sh_test")
load("@rules_shell//shell:sh_binary.bzl", "sh_binary")
load("//website:macros.bzl", "static_website", "website_theme")
load("//website/content:markdown.bzl", "markdown_assets")
load("//website/content:rst.bzl", "rst_assets")
load("//website/generators:mock.bzl", "mock_generator")
load("//website/generators:sphinx.bzl", "sphinx_generator")
load("//website/generators:yew.bzl", "yew_generator")

# Test content files
pkg_files(
    name = "test_content_files",
    srcs = glob(["test_content/**/*.md"]),
    strip_prefix = "test_content",
    prefix = "content",
)

pkg_filegroup(
    name = "test_content",
    srcs = [":test_content_files"],
)

# Test theme files
pkg_files(
    name = "test_theme_templates",
    srcs = glob(["test_theme/templates/**/*.html"]),
    strip_prefix = "test_theme",
    prefix = "theme",
)

pkg_filegroup(
    name = "test_theme",
    srcs = [":test_theme_templates"],
)

exports_files(["test_config.py"])

# Use static gzip wrapper script for compression tests
sh_binary(
    name = "gzip",
    srcs = ["gzip_wrapper.sh"],
)

# Test: Basic website generation with default Pelican generator
static_website(
    name = "test_basic_website",
    content = ":test_content",
    theme = ":test_theme",
    config = ":test_config.py",
    content_path = "content",
    output_path = "output",
    data = None,  # No additional data files needed for this test
    mappings = {},  # Empty mappings for minimal test
    # Use default generator (Pelican)
)

# Shell test to verify the website was generated correctly
sh_test(
    name = "website_generation_test",
    size = "small",
    srcs = ["run_website_tests.sh"],
    data = [
        ":test_basic_website",
    ],
    deps = [
        "@bazel_tools//tools/bash/runfiles",
    ],
)

# Test: Website generation with custom exclude patterns
static_website(
    name = "test_custom_exclude",
    content = ":test_content",
    theme = ":test_theme",
    config = ":test_config.py",
    content_path = "content",
    output_path = "output",
    data = None,
    mappings = {},  # Empty mappings for minimal test
    exclude = [
        # Custom exclude patterns (less than default)
        "theme/.webassets-cache",
    ],
)

# Test: Website generation with custom mappings
static_website(
    name = "test_custom_mappings",
    content = ":test_content",
    theme = ":test_theme",
    config = ":test_config.py",
    content_path = "content",
    output_path = "output",
    data = None,
    exclude = [],  # Empty excludes for this test
    mappings = {},  # Empty mappings to test flexibility
)

static_website(
    name = "test_with_compression",
    content = ":test_content",
    theme = ":test_theme",
    config = ":test_config.py",
    content_path = "content",
    output_path = "output",
    data = None,
    mappings = {},
    exclude = [],
    compressor = ":gzip",
    extension = "tar.gz",
)

# Shell test for parameterized tests
sh_test(
    name = "website_parameterized_test",
    size = "small",
    srcs = ["run_parameterized_tests.sh"],
    data = [
        ":test_custom_exclude",
        ":test_custom_mappings",
    ],
    deps = [
        "@bazel_tools//tools/bash/runfiles",
    ],
)

sh_test(
    name = "website_compression_test",
    size = "small",
    srcs = ["run_compression_test.sh"],
    data = [
        ":test_with_compression",
    ],
    deps = [
        "@bazel_tools//tools/bash/runfiles",
    ],
)

# ============================================================================
# Provider Architecture Tests
# ============================================================================

# Test content using new typed asset rules
markdown_assets(
    name = "test_markdown_content",
    srcs = glob(["test_content/**/*.md"]),
    strip_prefix = "test_content",
    prefix = "content",
)

rst_assets(
    name = "test_rst_content",
    srcs = [],  # No RST files yet, but tests the infrastructure
    prefix = "content",
)

# Test generators with WebsiteGeneratorInfo

mock_generator(
    name = "mock_gen",
    accepts = ["markdown", "rst", "jinja", "css", "js", "static"],
    output_path = "output",
)

sphinx_generator(
    name = "sphinx_gen",
    accepts = ["rst", "markdown", "sphinx_theme", "css", "js", "static"],
    output_path = "output",
)

yew_generator(
    name = "yew_gen",
    accepts = ["rust_component", "css", "js", "static", "wasm"],
    output_path = "output",
)

# Test: Mock generator with markdown assets
static_website(
    name = "test_mock_markdown",
    content = ":test_markdown_content",
    theme = ":test_theme",
    config = ":test_config.py",
    content_path = "content",
    output_path = "output",
    data = None,
    mappings = {},
    exclude = [],
    generator = ":mock_gen",
)

# Test: Sphinx generator skeleton with RST content
static_website(
    name = "test_sphinx_skeleton",
    content = ":test_rst_content",
    theme = ":test_theme",
    config = ":test_config.py",
    content_path = "content",
    output_path = "output",
    data = None,
    mappings = {},
    exclude = [],
    generator = ":sphinx_gen",
)

# Test: Yew generator skeleton
static_website(
    name = "test_yew_skeleton",
    content = ":test_rst_content",  # Yew doesn't use typical content
    theme = ":test_theme",
    config = ":test_config.py",
    content_path = "content",
    output_path = "output",
    data = None,
    mappings = {},
    exclude = [],
    generator = ":yew_gen",
)

# Test: Mock generator with mixed asset types
static_website(
    name = "test_mock_mixed",
    content = ":test_markdown_content",
    theme = ":test_theme",
    config = ":test_config.py",
    content_path = "content",
    output_path = "output",
    data = None,
    mappings = {},
    exclude = [],
    generator = ":mock_gen",
)

# Provider architecture test suite
sh_test(
    name = "provider_architecture_test",
    size = "small",
    srcs = ["run_provider_tests.sh"],
    data = [
        ":test_mock_markdown",
        ":test_sphinx_skeleton",
        ":test_yew_skeleton",
        ":test_mock_mixed",
    ],
    deps = [
        "@bazel_tools//tools/bash/runfiles",
    ],
)
