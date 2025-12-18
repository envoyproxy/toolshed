# arch_alias WORKSPACE Mode Test

This directory contains tests for the `arch_alias` repository rule in WORKSPACE mode.

## Purpose

This test validates:
1. The `arch_alias` repository rule works correctly in WORKSPACE mode
2. Multiple arch aliases can be created in the same workspace
3. The aliases resolve to the correct platform targets based on host architecture
4. Backward compatibility with existing WORKSPACE-based configurations

## Usage

### Running Tests Locally

From this directory:

```bash
bazel build //...
bazel test //...
```

### Verification

The test verifies that:
1. `@test_platform` resolves to `@platforms//host`
2. `@test_clang_platform` resolves to `@platforms//os:linux`
3. Both aliases can be used in `.bazelrc` configurations
4. The repository rule correctly detects host architecture

## Architecture Support

The test covers common architecture strings:
- `amd64` / `x86_64` - Intel/AMD 64-bit
- `aarch64` / `arm64` - ARM 64-bit

All architectures in the test map to known platform targets for validation.
