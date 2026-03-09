# Sanitizer libraries

This directory contains build rules for creating hermetic LLVM sanitizer libraries (MSAN, TSAN) that can be used with Envoy.

## Building

To build the libraries locally:

```bash
cd bazel
bazel build //compile:cxx_msan
bazel build //compile:cxx_tsan
```

This will produce:
- `bazel-bin/compile/msan-libs-x86_64.tar.gz`
- `bazel-bin/compile/tsan-libs-x86_64.tar.gz`

## Updating prebuilt versions

The sanitizer libraries are automatically built and published to GitHub releases. To update:

1. **Make changes** to the build configuration and merge them to main

2. **Create a release** with the naming format `bins-v{version}`

3. **Wait for CI** to build and publish the binaries to the release

4. **Get SHA256 hashes** for the published artifacts:
   ```bash
   curl -L https://github.com/envoyproxy/toolshed/releases/download/bins-v1.0.0/msan-libs-x86_64.tar.gz | sha256sum
   curl -L https://github.com/envoyproxy/toolshed/releases/download/bins-v1.0.0/tsan-libs-x86_64.tar.gz | sha256sum
   ```

5. **Update versions.bzl** with the new release tag and SHA256 values:
   ```python
   "bins_release": "1.0.0",
   "msan_libs_sha256": "...",  # Add actual SHA256
   "tsan_libs_sha256": "...",  # Add actual SHA256
   ```

## Using with WORKSPACE

In your WORKSPACE file:

```starlark
load("@envoy_toolshed//compile:sanitizer_libs.bzl", "setup_sanitizer_libs")

setup_sanitizer_libs()
```

This will create `@msan_libs` and `@tsan_libs` repositories you can use in your builds.

## Using with bzlmod (MODULE.bazel)

In your MODULE.bazel file:

```starlark
bazel_dep(name = "envoy_toolshed", version = "0.3.12")

# Setup sanitizer libraries
sanitizer_ext = use_extension("@envoy_toolshed//compile:extensions.bzl", "sanitizer_extension")
sanitizer_ext.setup()  # Uses default versions
use_repo(sanitizer_ext, "msan_libs", "tsan_libs")
```

Or with custom versions:

```starlark
sanitizer_ext = use_extension("@envoy_toolshed//compile:extensions.bzl", "sanitizer_extension")
sanitizer_ext.setup(
    msan_version = "0.1.34",
    msan_sha256 = "534e5e6893f177f891d78d6e85a80c680c84f0abd64681f8ddbf2f5457e97a52",
    tsan_version = "0.1.34",
    tsan_sha256 = "2cd571a07014972ff9bc0f189c5725c2ea121aeab0daa4c27ef171842ea13985",
)
use_repo(sanitizer_ext, "msan_libs", "tsan_libs")
```
