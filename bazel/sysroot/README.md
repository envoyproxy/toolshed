# Sysroots

This directory triggers the sysroot build workflow when modified.

## Available Sysroots

The workflow builds sysroots with the following configurations:

### glibc 2.31 (Current)
- **Base:** Debian bullseye
- **Compatibility:** Modern Linux distributions
- **Kernel Headers:** 5.10+ (from bullseye-backports)
- **Variants:**
  - Base: `sysroot-glibc2.31-{arch}.tar.xz`
  - With libstdc++13: `sysroot-glibc2.31-libstdc++13-{arch}.tar.xz`

### glibc 2.28 (Older)
- **Base:** Debian buster
- **Compatibility:** Ubuntu 18.04, RHEL 8, and older distributions
- **Kernel Headers:** 5.10+ (from buster-backports)
- **Variants:**
  - Base: `sysroot-glibc2.28-{arch}.tar.xz`
  - With libstdc++13: `sysroot-glibc2.28-libstdc++13-{arch}.tar.xz`

## Architecture Support

Both glibc versions are built for:
- `amd64` (x86_64)
- `arm64` (aarch64)

## Kernel Headers

All sysroots include modern kernel headers (5.10+) from Debian backports, which provide:
- **openat2.h** support (Linux 5.6+)
- Modern syscall definitions
- Up-to-date kernel API headers

This ensures that even older glibc sysroots can compile code using modern kernel features.

## Usage in Bazel

To use these sysroots in your Bazel WORKSPACE:

```starlark
load("@toolshed//bazel/sysroot:sysroot.bzl", "setup_sysroots")

# Use default glibc 2.31 with libstdc++13
setup_sysroots()

# Or use older glibc 2.28 for broader compatibility
setup_sysroots(
    glibc_version = "2.28",
    stdcc_version = "13",
)

# Or use base sysroot without libstdc++
setup_sysroots(
    glibc_version = "2.31",
    stdcc_version = None,
)

# Or use multiple sysroot configurations with name prefixes
setup_sysroots(
    glibc_version = "2.31",
    stdcc_version = "13",
    name_prefix = "new",
)
setup_sysroots(
    glibc_version = "2.28",
    stdcc_version = "13",
    name_prefix = "old",
)
# This creates @new_sysroot_linux_amd64, @new_sysroot_linux_arm64,
# @old_sysroot_linux_amd64, and @old_sysroot_linux_arm64
```

### Configuration Validation

The setup will automatically validate your configuration:
- **Unsupported glibc versions** will fail with a clear error message
- **Incompatible combinations** (e.g., requesting a variant that doesn't exist) will fail
- **Missing hashes** (e.g., for unreleased configurations) will fail with a helpful message

All SHA256 hashes are centrally managed in `versions.bzl` for ease of maintenance.

## Release Process

Sysroots are automatically built and published when:
1. Changes are pushed to `main` that affect this directory or the workflow
2. A release is created with name starting with `bazel-bins`

The artifacts are uploaded to the release assets.
