# Glint Toolchain

This directory contains the Bazel toolchain definition for glint, a whitespace linter written in Rust.

## Usage

The glint toolchain can be used in two ways:

### 1. As a toolchain dependency

Add the toolchain to your rule's `toolchains` attribute:

```python
my_rule(
    name = "example",
    toolchains = ["//toolchains/glint:current_glint_toolchain"],
)
```

Then in your rule implementation:

```python
load("//toolchains/glint:glint_toolchain.bzl", "get_glint_data")

def _my_rule_impl(ctx):
    glint_data = get_glint_data(ctx)
    glint_path = glint_data.glint
    # Use glint_path in your commands
```

### 2. Direct usage

The toolchain will automatically use prebuilt binaries for x86_64 (amd64) and aarch64 (arm64) architectures.
For other architectures, it will fall back to building glint from source using Rust.

## Architecture Support

- **x86_64/amd64**: Downloads prebuilt binary from GitHub releases
- **aarch64/arm64**: Downloads prebuilt binary from GitHub releases
- **Other architectures**: Builds from source using rules_rust

## Configuration

The toolchain is automatically registered when using `setup_glint()` in your WORKSPACE file.
