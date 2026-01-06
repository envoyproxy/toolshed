# arch_alias Tests

This directory contains comprehensive tests for the `arch_alias` functionality in both WORKSPACE and bzlmod modes.

## Directory Structure

```
test/
└── arch_alias/       # Tests for arch_alias functionality
    ├── bzlmod/       # Tests for bzlmod mode (MODULE.bazel)
    │   ├── MODULE.bazel  # Bzlmod test module configuration
    │   ├── BUILD.bazel   # Test targets
    │   └── .bazelrc      # Test configuration
    ├── workspace/    # Tests for WORKSPACE mode (legacy)
    │   ├── WORKSPACE     # WORKSPACE test configuration
    │   ├── BUILD.bazel   # Test targets
    │   └── .bazelrc      # Test configuration
    └── README.md     # This file
```

## Purpose

These tests validate:
1. **Bzlmod Mode** (`arch_alias/bzlmod/`):
   - The `arch_alias_ext` module extension works correctly
   - Multiple arch aliases can be created in the same module
   - The aliases resolve to correct platform targets based on host architecture
   - Integration with BCR presubmit checks

2. **WORKSPACE Mode** (`arch_alias/workspace/`):
   - The `arch_alias` repository rule works correctly
   - Backward compatibility with existing WORKSPACE-based configurations
   - Multiple aliases can coexist in the same workspace

## Running Tests

### Test Bzlmod Mode

```bash
cd bazel/test/arch_alias/bzlmod
bazel build //...
bazel test //...
```

### Test WORKSPACE Mode

```bash
cd bazel/test/arch_alias/workspace
bazel build //...
bazel test //...
```

### Verify Platform Aliases

You can inspect the created aliases:

```bash
# In bzlmod_test or workspace_test directory
bazel query @test_platform//...
bazel query @test_clang_platform//...
```

## BCR Integration

The `bzlmod_test/` follows BCR best practices and is suitable for BCR presubmit testing:
- Located in the standard `test/` directory structure
- Uses `local_path_override` to test the parent module
- Can be run independently or as part of CI/CD
- Tests both single and multiple alias scenarios

## Architecture Coverage

Both tests cover common architecture identifiers:
- `amd64` / `x86_64` - Intel/AMD 64-bit
- `aarch64` / `arm64` - ARM 64-bit

The aliases map to platform targets from `@platforms` for validation.

## What Gets Tested

1. **Repository Creation**: Aliases create proper external repositories
2. **Platform Resolution**: Aliases resolve to correct platform targets based on host arch
3. **Build Configuration**: Aliases work correctly in `.bazelrc` with `--host_platform`
4. **Multiple Aliases**: Multiple aliases can coexist and work independently
5. **API Compatibility**: Both WORKSPACE and bzlmod APIs function correctly
