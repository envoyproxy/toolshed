# Sanitizer, libcxx, and minimal LLVM libraries

This directory contains build rules for creating and downloading prebuilt LLVM libraries for use with Envoy, including:

- **Sanitizer libraries** (MSAN, TSAN) for use with sanitizer builds
- **libcxx bundles** for cross-compilation with `toolchains_llvm`
- **Minimal LLVM** — filtered, stripped LLVM distributions for the three supported platforms

## Sanitizer libraries (MSAN, TSAN)

### Building

To build the libraries locally:

```bash
cd bazel
bazel build //compile:cxx_msan
bazel build //compile:cxx_tsan
```

This will produce:
- `bazel-bin/compile/msan-libs-x86_64.tar.gz`
- `bazel-bin/compile/tsan-libs-x86_64.tar.gz`

### Updating prebuilt versions

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

### Direct `.bzl` load

```starlark
load("@envoy_toolshed//compile:sanitizer_libs.bzl", "setup_sanitizer_libs")

setup_sanitizer_libs()
```

This will create `@msan_libs` and `@tsan_libs` repositories you can use in your builds.

GCC-specific targets are selected from the compiler reported by the resolved C++ toolchain.
Consumers registering a GCC `cc_toolchain` get the matching libstdc++ targets automatically;
they do not need to set toolshed's internal `//compile:use_gcc_toolchain` flag.

### Using with bzlmod (MODULE.bazel)

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

## Shared libunwind for sanitizer builds

ASAN intercepts `_Unwind_RaiseException` and finds the real implementation with
`dlsym(RTLD_NEXT)`. A static libunwind in the executable is invisible to that
lookup, which can fall through to Rust std's `libgcc_s` dependency. Mixing the
unwinders breaks Rust panics in dynamic modules. Linking LLVM libunwind as a
shared library lets these calls resolve to the same unwinder.

The upstream LLVM 22.1.8 Linux shared libunwind requires glibc 2.34, newer than
toolshed's glibc 2.31 sysroot. This package builds only shared libunwind from
`@llvm_source`, using the LLVM toolchain, compiler-rt builtins, and that sysroot.
It does not change the MSAN/TSAN libraries or the sysroot.

Build and verify (x86_64 Linux only):

```bash
cd bazel
bazel build //compile:cxx_unwind
bazel test //compile/test:libunwind_shared_test
```

The output `bazel-bin/compile/unwind-llvm22.1.8-x86_64.tar.xz` contains
`unwind-libs-x86_64/lib/libunwind.so.1`. The manual test inspects the **built**
library, not a downloaded artifact, checking its SONAME, absence of a `libgcc_s`
dependency, and glibc version requirements. It also runs in Linux CI.
Release preparation fills `VERSIONS["unwind_libs_sha256"]` after the `bins-v*`
release publishes the artifact. Until then, the repository rule rejects the
empty hash; consumers can supply a published release's `version` and `sha256`.

In `MODULE.bazel`:

```starlark
unwind_ext = use_extension("@envoy_toolshed//compile:extensions.bzl", "unwind_extension")
unwind_ext.setup()
use_repo(unwind_ext, "unwind_libs")
```

The repository exposes `@unwind_libs//:libunwind_so` (the shared file) and
`@unwind_libs//:libunwind` (a public `cc_import`). Add the import to your ASAN
configuration's dependencies so Bazel manages solib rpaths and runfiles:

```starlark
cc_library(
    name = "unwinder",
    linkopts = select({
        ":linux_asan_build": ["-unwindlib=none"],
        "//conditions:default": [],
    }),
    deps = select({
        ":linux_asan_build": ["@unwind_libs//:libunwind"],
        "//conditions:default": [],
    }),
)
```

Here `:linux_asan_build` is the consumer's Linux ASAN `config_setting`.
`-unwindlib=none` prevents Clang from adding a static unwinder even when other
flags include `-static-libgcc`. Also disable any explicit static `libunwind.a`
dependency in that configuration. Alternatively, a consumer's own `cc_import`
can set `shared_library = "@unwind_libs//:libunwind_so"`.
Verify that the executable's `DT_NEEDED` lists `libunwind.so.1` before
`libgcc_s.so.1`, so ASAN and dynamically loaded Rust modules use LLVM's unwinder.

## libcxx bundles (for cross-compilation)

Prebuilt libcxx bundles provide the `libc++.a`, `libc++abi.a`, and `libunwind.a` static
libraries for each target architecture. These are intended for use with `toolchains_llvm`
when cross-compiling (e.g., building aarch64 binaries on an x86_64 host).

The bundles are downloaded from GitHub releases and expose the following Bazel targets:

- `@libcxx_libs_aarch64//:libs` — filegroup of all `.a` files for aarch64
- `@libcxx_libs_aarch64//:libcxx_libs` — `cc_library` wrapping all libs (alwayslink)
- `@libcxx_libs_aarch64//:headers` — filegroup of the `__config_site` header
- Same targets available in `@libcxx_libs_x86_64`

### Updating prebuilt versions

1. **Build the bundles** by triggering the CI workflow (see `compile/BUILD` for `libcxx_{arch}` targets)

2. **Create a release** with the naming format `bins-v{version}`

3. **Wait for CI** to publish the binaries to the release

4. **Get SHA256 hashes** for the published artifacts:
   ```bash
   curl -L https://github.com/envoyproxy/toolshed/releases/download/bins-v{version}/libcxx-llvm{llvm_version}-aarch64.tar.xz | sha256sum
   curl -L https://github.com/envoyproxy/toolshed/releases/download/bins-v{version}/libcxx-llvm{llvm_version}-x86_64.tar.xz | sha256sum
   ```

5. **Update versions.bzl** with the SHA256 values:
   ```python
   "libcxx_libs_sha256": {
       "aarch64": "...",  # Add actual SHA256
       "x86_64": "...",   # Add actual SHA256
   },
   ```

### Direct `.bzl` load

```starlark
load("@envoy_toolshed//compile:libcxx_libs.bzl", "setup_libcxx_libs")

setup_libcxx_libs()
```

This will create `@libcxx_libs_aarch64` and `@libcxx_libs_x86_64` repositories.

### Using with bzlmod (MODULE.bazel)

In your MODULE.bazel file:

```starlark
bazel_dep(name = "envoy_toolshed", version = "0.3.29")

# Setup prebuilt libcxx for cross-compilation
libcxx_libs_ext = use_extension("@envoy_toolshed//compile:extensions.bzl", "libcxx_libs_extension")
libcxx_libs_ext.setup()
use_repo(libcxx_libs_ext, "libcxx_libs_aarch64", "libcxx_libs_x86_64")
```

Or with custom versions:

```starlark
libcxx_libs_ext = use_extension("@envoy_toolshed//compile:extensions.bzl", "libcxx_libs_extension")
libcxx_libs_ext.setup(
    aarch64_sha256 = "...",
    x86_64_sha256 = "...",
)
use_repo(libcxx_libs_ext, "libcxx_libs_aarch64", "libcxx_libs_x86_64")
```

### Cross-compilation test

Cross-compilation tests are provided in `compile/test/`. They build simple C++ programs and verify the compiled binary is of the correct ELF architecture.

To run the architecture tests (requires the cross-compilation toolchain to be configured):

```bash
# Test aarch64 cross-compilation (hello world)
bazel test //compile/test:cross_compile_aarch64_test \
  --platforms=@toolchains_llvm//platforms:linux-aarch64

# Test x86_64 cross-compilation (hello world)
bazel test //compile/test:cross_compile_x86_64_test \
  --platforms=@toolchains_llvm//platforms:linux-x86_64
```

### Unwind tests

The unwind tests verify that `libunwind.a` is **statically linked** into the `test_unwind` binary,
rather than just checking the ELF architecture. They use `llvm-nm` to check for a defined
`_Unwind_RaiseException` symbol (indicating `libunwind.a` was linked in) and `llvm-readelf`
to confirm there is no `libgcc_s` dynamic dependency (which would indicate a fallback to the
system unwinder).

The `libunwind` flag defaults to `False` in the Envoy registry build of `toolchains_llvm`, so
the positive tests must enable it with `--@toolchains_llvm//toolchain/config:libunwind=True`.

```bash
# Test aarch64 cross-compilation with libunwind statically linked
bazel test //compile/test:cross_compile_aarch64_unwind_test \
  --platforms=@toolchains_llvm//platforms:linux-aarch64 \
  --@toolchains_llvm//toolchain/config:libunwind=True

# Test x86_64 cross-compilation with libunwind statically linked
bazel test //compile/test:cross_compile_x86_64_unwind_test \
  --platforms=@toolchains_llvm//platforms:linux-x86_64 \
  --@toolchains_llvm//toolchain/config:libunwind=True
```

**Negative unwind tests** verify that libunwind is *not* statically linked when
`--@toolchains_llvm//toolchain/config:libunwind=False` is passed:

```bash
# Verify libunwind is NOT linked for aarch64 when disabled
bazel test //compile/test:cross_compile_aarch64_no_unwind_test \
  --platforms=@toolchains_llvm//platforms:linux-aarch64 \
  --@toolchains_llvm//toolchain/config:libunwind=False

# Verify libunwind is NOT linked for x86_64 when disabled
bazel test //compile/test:cross_compile_x86_64_no_unwind_test \
  --platforms=@toolchains_llvm//platforms:linux-x86_64 \
  --@toolchains_llvm//toolchain/config:libunwind=False
```

## Minimal LLVM artifact

The minimal LLVM artifact is a filtered and stripped subset of the upstream LLVM
release tarballs. It retains only the tools and libraries actually needed by the
`toolchains_llvm` cc toolchain, envoy CI, and the toolshed `clang_tidy`
integration, while discarding large unused components (bugpoint, opt, llc, lldb,
mlir tools, dev headers, docs, examples, redundant static archives, etc.).

Three platform artifacts are produced and published to the `bins-v{version}` GitHub
release:

| Artifact | Platform |
|---|---|
| `llvm-minimal-{llvm_version}-Linux-X64.tar.zst` | Linux x86_64 |
| `llvm-minimal-{llvm_version}-Linux-ARM64.tar.zst` | Linux aarch64 |
| `llvm-minimal-{llvm_version}-macOS-ARM64.tar.zst` | macOS arm64 |

### Allowlist — single source of truth

The exact set of tools and libraries to keep is defined in
**`bazel/compile/llvm_minimal.bzl`** as two Starlark constants:

- `LLVM_MINIMAL_BINS` — list of `bin/` tool names to keep.
  Symlinks (e.g. `clang++` → `clang`, `ld.lld` → `lld`) are preserved as
  symlinks rather than dereferenced, so the binary is not duplicated.
- `LLVM_MINIMAL_LIB_GLOBS` — list of `lib/` and `include/` patterns to keep,
  documented inline with the rationale for each entry.

To change what is included, edit those two lists in `llvm_minimal.bzl` and
rebuild/re-release. No other file needs updating.

### Building locally

```bash
cd bazel

# Build a single platform artifact (Linux x86_64 example)
bazel build //compile:llvm_minimal_linux_x86_64

# Build all three platform artifacts
bazel build //compile:llvm_minimal_linux_x86_64 \
            //compile:llvm_minimal_linux_arm64 \
            //compile:llvm_minimal_macos_arm64
```

The outputs land in `bazel-bin/compile/`:
- `llvm-minimal-{llvm_version}-Linux-X64.tar.zst`
- `llvm-minimal-{llvm_version}-Linux-ARM64.tar.zst`
- `llvm-minimal-{llvm_version}-macOS-ARM64.tar.zst`

The build targets download the full upstream LLVM tarballs via the
`llvm_tarball_*` repository rules (set up by `setup_llvm_minimal_build()` in
`llvm_minimal.bzl`, wired via `llvm_minimal_build_extension` in
`extensions.bzl`). The strip rule then filters the tarball to the allowlist,
strips ELF/Mach-O binaries with hermetic LLVM tools, and repacks with hermetic
`bsdtar` + `zstd`.

### Publishing

The `.tar.zst` artifacts are uploaded to a `bins-v{version}` GitHub release.
The `release.yml` workflow (bazel/prepare) then computes their SHA256 hashes and opens
a PR that updates `bazel/versions.bzl`.

### Updating prebuilt versions

1. **Rebuild** with `bazel build //compile:llvm_minimal_*`.

2. **Create/publish** a `bins-v{version}` release and upload the three `.tar.zst`
   files alongside the other artifacts.

3. **Run the `release.yml` workflow** (manually via `workflow_dispatch` - bazel release or prepare)
   to compute and PR the new SHA256 hashes into `bazel/versions.bzl` under
   `llvm_minimal_sha256`.

4. **Merge the hash PR** — downstream consumers can now consume the artifacts.

### Direct `.bzl` load

```starlark
load("@envoy_toolshed//compile:llvm_minimal.bzl", "setup_llvm_minimal")

setup_llvm_minimal()
```

This creates three repositories:
- `@llvm_minimal_linux_x64`
- `@llvm_minimal_linux_arm64`
- `@llvm_minimal_macos_arm64`

Each exposes `bin`, `lib`, `include`, and `all` filegroup targets.

### Using with bzlmod (MODULE.bazel)

```starlark
bazel_dep(name = "envoy_toolshed", version = "...")

llvm_minimal_ext = use_extension("@envoy_toolshed//compile:extensions.bzl", "llvm_minimal_extension")
llvm_minimal_ext.setup()  # Uses default versions from VERSIONS
use_repo(llvm_minimal_ext, "llvm_minimal_linux_x64", "llvm_minimal_linux_arm64", "llvm_minimal_macos_arm64")
```

Or with custom versions:

```starlark
llvm_minimal_ext = use_extension("@envoy_toolshed//compile:extensions.bzl", "llvm_minimal_extension")
llvm_minimal_ext.setup(
    linux_x64_sha256 = "...",
    linux_arm64_sha256 = "...",
    macos_arm64_sha256 = "...",
)
use_repo(llvm_minimal_ext, "llvm_minimal_linux_x64", "llvm_minimal_linux_arm64", "llvm_minimal_macos_arm64")
```

SHA256 values default to `VERSIONS["llvm_minimal_sha256"][platform]` from
`versions.bzl`.  Empty strings (the placeholder state before first release)
cause `setup_llvm_minimal()` to create a stub empty repository instead of
downloading, so builds that don't reference the repo are not broken.

### Host LLVM and toolchain alias

The `llvm_toolchain_alias_extension` creates `@llvm_toolchain_llvm`, backed by
the matching minimal LLVM artifact by default. Its `host` tag can instead use
a local LLVM installation; it may only be declared once by the root module:

```starlark
llvm = use_extension("@envoy_toolshed//compile:extensions.bzl", "llvm_toolchain_alias_extension")
llvm.host(path = "/usr/lib/llvm-22", llvm_version = "22.1.8")
use_repo(llvm, "llvm_toolchain_llvm")
```

The repository exports `llvm.bzl` with `LLVM_VERSION`, `LLVM_MAJOR`,
`LLVM_MAJOR_MINOR`, `LLVM_LIB_DIR`, and `LLVM_IS_HOST`. It also exposes
`libclang_cpp`, `libllvm`, and `clang_tooling_headers` targets, in addition to
the LLVM toolchain targets.
