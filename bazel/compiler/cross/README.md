# Cross-compilation libc++ libraries

This package provides prebuilt `libc++.a`, `libc++abi.a`, and `libunwind.a`
extracted from official LLVM release tarballs for use when cross-compiling.
The libraries are repackaged into lean tarballs published to GitHub releases —
no local compilation required.

This keeps the sysroot lean (glibc headers/libs only) while making the
libc++ static libraries available as a separate Bazel repository.

## Building and publishing

To build the repackaged tarballs locally:

```bash
cd bazel
bazel build //compiler/cross:cxx_cross_aarch64
bazel build //compiler/cross:cxx_cross_x86_64
```

This will produce:
- `bazel-bin/compiler/cross/cross-llvm18.1.8-aarch64.tar.xz`
- `bazel-bin/compiler/cross/cross-llvm18.1.8-x86_64.tar.xz`

> **Note:** Building these targets downloads the full LLVM prebuilt tarballs
> (~500 MB for aarch64, ~900 MB for x86_64). They are cached after the first
> download.

## Updating published versions

The cross libs tarballs are automatically packaged and published to GitHub
releases. To update:

1. **Update sha256s** in `MODULE.bazel` for `llvm_prebuilt_aarch64` and
   `llvm_prebuilt_x86_64` if upgrading LLVM.

2. **Create a release** with the naming format `bins-v{version}`.

3. **Wait for CI** to build and publish the tarballs to the release.

4. **Get SHA256 hashes** for the published artifacts:
   ```bash
   curl -L https://github.com/envoyproxy/toolshed/releases/download/bins-v0.1.47/cross-llvm18.1.8-aarch64.tar.xz | sha256sum
   curl -L https://github.com/envoyproxy/toolshed/releases/download/bins-v0.1.47/cross-llvm18.1.8-x86_64.tar.xz | sha256sum
   ```

5. **Update `versions.bzl`** with the new SHA256 values:
   ```python
   "libcxx_cross_sha256": {
       "aarch64": "...",
       "x86_64": "...",
   },
   ```

## Using with WORKSPACE

```starlark
load("@envoy_toolshed//compiler/cross:libcxx_cross.bzl", "setup_libcxx_cross")

# Call once per target architecture
setup_libcxx_cross(target_arch = "aarch64")
setup_libcxx_cross(target_arch = "x86_64")
```

This creates `@libcxx_cross_aarch64` and `@libcxx_cross_x86_64` repositories,
each exposing:

- `:libcxx` — `libc++.a`
- `:libcxxabi` — `libc++abi.a`
- `:libunwind` — `libunwind.a`
- `:libcxx_cross` — all three bundled together
- `:config_site_header` — `__config_site` header filegroup

## Using with bzlmod (MODULE.bazel)

```starlark
bazel_dep(name = "envoy_toolshed", version = "0.3.12")

# Setup cross-compilation libc++ libraries (one call per arch)
libcxx_cross_ext = use_extension("@envoy_toolshed//compiler/cross:extensions.bzl", "libcxx_cross_extension")
libcxx_cross_ext.setup(target_arch = "aarch64")
libcxx_cross_ext.setup(target_arch = "x86_64")
use_repo(libcxx_cross_ext, "libcxx_cross_aarch64", "libcxx_cross_x86_64")
```

Or with custom versions:

```starlark
libcxx_cross_ext = use_extension("@envoy_toolshed//compiler/cross:extensions.bzl", "libcxx_cross_extension")
libcxx_cross_ext.setup(
    target_arch = "aarch64",
    version = "0.1.47",
    sha256 = "...",
)
use_repo(libcxx_cross_ext, "libcxx_cross_aarch64")
```
