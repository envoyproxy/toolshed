# arch_alias Tests

This directory contains tests for the `arch_alias` repository rule and module extension.

## Test Modes

### bzlmod/
Tests the `arch_alias_ext` module extension for bzlmod compatibility. This is the recommended approach for new projects using Bazel's module system.

### workspace/
Tests the `arch_alias` repository rule in WORKSPACE mode for backward compatibility with existing configurations.

## What is arch_alias?

`arch_alias` enables architecture-specific platform selection by detecting the host CPU architecture and creating aliases that resolve to different platform targets. This is particularly useful for:

- Remote Build Execution (RBE) with architecture-specific platforms
- Cross-compilation scenarios
- CI/CD pipelines that need to adapt to different host architectures

## Running All Tests

From this directory:
```bash
# Test bzlmod mode
cd bzlmod && bazel build //... && bazel test //...

# Test workspace mode
cd workspace && bazel build //... && bazel test //...
```

See the individual subdirectories for detailed documentation on each test mode.
