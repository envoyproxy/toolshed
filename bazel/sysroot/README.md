# Sysroots

This directory contains both sysroot repository rules for downloading pre-built sysroots and build targets for creating new sysroots.

## Available Sysroots

The workflow builds sysroots with the following configurations:

### glibc 2.31 (Current)
- **Base:** Debian bullseye
- **Compatibility:** Modern Linux distributions
- **Kernel Headers:** 5.10+ (from bullseye-backports)
- **Variants:**
  - **Base:** `sysroot-glibc2.31-{arch}.tar.xz`
  - **With libstdc++13:** `sysroot-glibc2.31-libstdc++13-{arch}.tar.xz`

### glibc 2.28 (Older)
- **Base:** Debian buster
- **Compatibility:** Ubuntu 18.04, RHEL 8, and older distributions
- **Kernel Headers:** 5.10+ (from buster-backports)
- **Variants:**
  - **Base:** `sysroot-glibc2.28-{arch}.tar.xz`
  - **With libstdc++13:** `sysroot-glibc2.28-libstdc++13-{arch}.tar.xz`

Each base sysroot includes the `libgcc_s.so.1` runtime and an unversioned
`usr/lib/<triple>/libgcc_s.so` linker script so literal `-lgcc_s` links resolve
(needed by, for example, rustc). It does not include `libgcc.a` or libstdc++;
Clang consumers should use `-rtlib=compiler-rt`. C++ standard-library headers and
libraries for GCC and LLVM come from the selected toolchain, not the sysroot.

### GCC and LLVM share the base sysroot

Both GCC and LLVM toolchains use the **base** sysroot. The libstdc++13 sysroot
variant continues to be built and published for consumers that need it.
Do not pass that variant to `gcc.toolchain(sysroot = ...)`: GCC must use the
base sysroot so `-l:libstdc++.a` resolves to GCC's own archive.

`--config=gcc` selects hermetic GCC 13.4.0; `--config=rbe-gcc` retains the
existing remote execution platforms. Both GCC target architectures execute on
Linux x86_64 (including aarch64 cross-compilation). GCC supplies its own
libstdc++, libgcc, libgcc_eh, and crtbegin/crtend objects; glibc supplies
crt1/crti/crtn from this sysroot. GCC links its C++ runtime statically.
LLVM continues to supply compiler-rt and libc++ from its own toolchain.
The GCC 13.4.0 release has no aarch64-hosted archive (native sibling releases
start at newer GCC versions), so there is no `linux_arm64_gcc` execution
platform: aarch64 GCC actions run on x86_64 workers.

The pinned archives come from
[f0rmiga/gcc-builds release 18082025](https://github.com/f0rmiga/gcc-builds/releases/tag/18082025),
the same source used by envoyproxy/envoy#39632. Empirical inspection of the
SHA-pinned archives measured maximum GLIBC requirements of **2.26 (x86_64)**
and **2.25 (aarch64)** in the shared libstdc++ siblings. The static archives'
`nm -u` output contains no GLIBC version tags, `__isoc23_*`, or
`__libc_single_threaded`; absence of version tags alone is not proof of
compatibility. `//toolchains/gcc:linux_{x86_64,aarch64}_runtime_abi_test` also
resolves every strong undefined name in libstdc++.a/libgcc.a/libgcc_eh.a against
the other runtimes, GCC CRT, and base-sysroot exports at or below GLIBC_2.31
(1,383 x86_64 and 1,365 aarch64 names in the pinned archives). The existing
stdlib fixture linked with these inputs on both architectures with a measured
maximum GLIBC_2.25 and no dynamic libstdc++/libgcc_s dependencies.
The repository rule removes the archive's bundled libc sysroot and explicitly
uses toolshed's glibc 2.31 base sysroot.
Replacement GCC archives **must build their target runtimes against glibc
<= 2.31**; changing `--sysroot` cannot lower the glibc requirement of an
already-built libstdc++.

Downstreams can instantiate the downloads with `gcc_extension` from
`//toolchains/gcc:extensions.bzl`, using a `toolchain(name = ..., arch =
"x86_64" | "aarch64", sysroot = "@sysroot_linux_...//sysroot")` tag per target.
Downstreams must instantiate this extension and register their own toolchains;
toolshed's registrations are dev-only. Register GCC before LLVM, as in
toolshed's `MODULE.bazel`.
Each generated repository exports `:cc_toolchain`, `:config`, `:files`,
`:libstdcxx` (headers and static library), and `:libgcc` (static runtime archives).
The base sysroot label must point directly into the `sysroot` package, not its
root-package alias.

Consumers compiling with a non-GCC toolchain but needing the libstdc++ ABI
(for example, Envoy's `compat/openssl/prefixer` linking against prebuilt
`libclang-cpp.so`) should use the GCC repository rather than a second sysroot:

```starlark
cc_binary(
    name = "prefixer",
    srcs = ["prefixer.cpp"],
    copts = ["-nostdinc++", "-stdlib=libstdc++"],
    deps = [
        "@gcc_linux_x86_64//:libstdcxx",
        # ... clang-tooling dependencies ...
    ],
)
```

Use the appropriate `@<gcc_repo>//:libstdcxx` for the compilation architecture.
Its `CcInfo` supplies headers as compile inputs, include directories, and the
static archive as a link input, including on RBE. Keep libc/CRT from the base
sysroot: adding `-L` for a libstdc++13 sysroot's entire `usr/lib/<triple>` can mix
libc/libpthread versions and produce `GLIBC_PRIVATE` and `__libc_csu_*` errors.

**Release TODO:** the next `bins-v*` release must regenerate both wee8
libstdcxx archives and refresh `VERSIONS["wee8_sha256"][arch]["libstdcxx"]`
before downstream consumption (including envoyproxy/envoy#39632). Existing
x86_64 libstdcxx artifacts were built against host glibc 2.39 and are not
compatible with this floor; aarch64 libstdcxx remains an incompatible prebuilt
stub until its first archive/hash is published. `//v8:wee8_packages` builds
all four arch/stdlib combinations without consuming these prebuilts.
`//compile/test:wee8_prebuilt_link_test` links wasm C-API entry points against
`//v8:wee8`, then checks the executable's GLIBC versions and static C++ runtime.
The GCC CI leg includes it, but the known-incompatible x86_64 hash gates it off
until replaced; the archive symbol-name scan remains an early pre-filter.

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

### Repository layout

Archives are extracted into the repository's `sysroot/` directory. The public
`:sysroot` target is an alias to `//sysroot:sysroot`, a single source-directory
artifact rather than a filegroup expanding every file. This gives compile actions
one sandbox symlink and one merkle-tree node, avoiding Bazel 9's multi-file sysroot
warning. Files named with `:` and `*.pl` files are removed after extraction because
a directory artifact cannot exclude individual files.

The Linux `:headers`, `:libs`, and `:toolchain_sysroot` targets remain public:
headers and libraries still provide individual files, while `:toolchain_sysroot`
wraps the directory artifact. Their filegroups live inside the `sysroot` package
because Bazel globs cannot cross package boundaries.

Raw file labels now use the `sysroot` package, for example
`@sysroot_linux_amd64//sysroot:usr/include/stdio.h` instead of
`@sysroot_linux_amd64//:usr/include/stdio.h`. Downstream Envoy's
`source/extensions/dynamic_modules/sdk/rust/BUILD` must update its raw `stdio.h`
label accordingly; `@sysroot_linux_amd64//:headers` is unchanged.

Configure LLVM's `llvm.sysroot` with
`@sysroot_linux_amd64//sysroot:sysroot` (and the arm64 equivalent).
LLVM derives its sysroot path from the label's package, not the alias's resolved
artifact, so the direct label is required to get
`external/<canonical-repository-name>/sysroot`. macOS repositories use the same
directory-and-alias layout, including when the SDK is empty.

### Direct `.bzl` load

To use these sysroots via a direct `.bzl` load:

```starlark
load("@toolshed//bazel/sysroot:sysroot.bzl", "setup_sysroots")

# Use default glibc 2.31 sysroot
setup_sysroots()

# Or use older glibc 2.28 for broader compatibility
setup_sysroots(
    glibc_version = "2.28",
)

# Or use the libstdc++13 sysroot variant
setup_sysroots(
    stdcc_version = "13",
)

# Or use multiple sysroot configurations with name prefixes
setup_sysroots(
    glibc_version = "2.31",
    name_prefix = "new",
)
setup_sysroots(
    glibc_version = "2.28",
    name_prefix = "old",
)
# This creates @new_sysroot_linux_amd64, @new_sysroot_linux_arm64,
# @old_sysroot_linux_amd64, and @old_sysroot_linux_arm64
```

### MODULE.bazel (bzlmod) Mode

To use these sysroots in your MODULE.bazel file:

```starlark
# Add envoy_toolshed as a dependency
bazel_dep(name = "envoy_toolshed", version = "0.3.12")

# Setup sysroots using the extension
sysroot_ext = use_extension("@envoy_toolshed//bazel/sysroot:extensions.bzl", "sysroot_extension")

# Use default glibc 2.31 sysroot
sysroot_ext.setup()

# Or configure an older glibc sysroot:
# sysroot_ext.setup(
#     glibc_version = "2.28",
# )

# Or use the libstdc++13 sysroot variant:
# sysroot_ext.setup(
#     stdcc_version = "13",
# )

# Or use multiple sysroot configurations with name prefixes:
# sysroot_ext.setup(
#     glibc_version = "2.31",
#     name_prefix = "new",
# )
# sysroot_ext.setup(
#     glibc_version = "2.28",
#     name_prefix = "old",
# )

# Make the sysroots available to your module
use_repo(sysroot_ext, "sysroot_linux_amd64", "sysroot_linux_arm64")

# If using name prefixes, specify all repository names:
# use_repo(sysroot_ext, "new_sysroot_linux_amd64", "new_sysroot_linux_arm64",
#                       "old_sysroot_linux_amd64", "old_sysroot_linux_arm64")
```

### Configuration Validation

The setup will automatically validate your configuration:
- **Unsupported glibc versions** will fail with a clear error message
- **Unsupported architectures** will fail with a clear error message
- **Missing hashes** (e.g., for unreleased configurations) will fail with a helpful message

All SHA256 hashes are centrally managed in `versions.bzl` as
`sysroot_hashes[glibc_version][variant][arch]`, where variant is `"base"` or `"13"`.

## Building Sysroots with Bazel

You can build sysroots locally using Bazel. The builds are marked as `manual` so they won't be built by default.

### Available Build Targets

All sysroot build targets are in the `//sysroot` package (from the `bazel/` directory):

```bash
# Build ALL sysroots at once (from the bazel/ directory):
cd bazel
bazel build //sysroot:sysroots

# Or build specific sysroots:
bazel build //sysroot:sysroot_glibc231_amd64
bazel build //sysroot:sysroot_glibc231_arm64
bazel build //sysroot:sysroot_glibc231_libstdcxx_amd64
bazel build //sysroot:sysroot_glibc231_libstdcxx_arm64
bazel build //sysroot:sysroot_glibc228_amd64
bazel build //sysroot:sysroot_glibc228_arm64
bazel build //sysroot:sysroot_glibc228_libstdcxx_amd64
bazel build //sysroot:sysroot_glibc228_libstdcxx_arm64
```

The built sysroots will be in `bazel-bin/sysroot/` directory.

### Direct Script Usage

You can also use the build script directly for custom configurations:

```bash
# Basic usage
cd bazel
bazel run //sysroot:build_sysroot -- \
  --arch amd64 \
  --glibc 2.31 \
  --debian bullseye \
  --workdir "$PWD/sysroot-build" \
  --output "$PWD/sysroot-glibc2.31-amd64.tar.xz"

# Build with libstdc++13
bazel run //sysroot:build_sysroot -- \
  --arch amd64 \
  --glibc 2.31 \
  --debian bullseye \
  --variant libstdcxx \
  --ppa-toolchain focal \
  --stdcc 13 \
  --workdir "$PWD/sysroot-build" \
  --output "$PWD/sysroot-glibc2.31-libstdc++13-amd64.tar.xz"

# Keep specific directories (e.g., keep bin and sbin for debugging)
bazel run //sysroot:build_sysroot -- \
  --arch amd64 \
  --glibc 2.31 \
  --debian bullseye \
  --workdir "$PWD/sysroot-build" \
  --output "$PWD/sysroot-glibc2.31-amd64.tar.xz" \
  --keep-dirs bin,sbin

# Remove additional directories beyond the defaults
bazel run //sysroot:build_sysroot -- \
  --arch amd64 \
  --glibc 2.31 \
  --debian bullseye \
  --workdir "$PWD/sysroot-build" \
  --output "$PWD/sysroot-glibc2.31-amd64.tar.xz" \
  --remove-dirs usr/games,usr/local

# Skip cleanup entirely (keep everything)
bazel run //sysroot:build_sysroot -- \
  --arch amd64 \
  --glibc 2.31 \
  --debian bullseye \
  --workdir "$PWD/sysroot-build" \
  --output "$PWD/sysroot-glibc2.31-amd64.tar.xz" \
  --skip-cleanup
```

#### Cleanup Configuration

By default, the build script removes directories that are typically not needed for cross-compilation:
- System directories: `boot`, `dev`, `proc`, `sys`, `run`, etc.
- Binaries: `bin`, `sbin`, `usr/sbin`, and standalone utilities
- Documentation: `usr/share/doc`, `usr/share/man`, `usr/share/info`
- Other: `var`, `tmp`, `home`, `opt`, etc.

You can customize this behavior:
- **`--keep-dirs`**: Comma-separated list of directories to preserve from the default cleanup
- **`--remove-dirs`**: Comma-separated list of additional directories to remove
- **`--skip-cleanup`**: Skip the cleanup phase entirely

### Requirements

Building sysroots requires:
- `sudo` access (for debootstrap and chroot operations)
- `debootstrap` package installed
- Linux host (uses debootstrap and chroot)

**Note:** These builds are non-hermetic and require network access to download Debian packages.

## Release Process

Sysroots are automatically built and published when:
1. Changes are pushed to `main` that affect this directory or the workflow
2. A release is created with name starting with `bins`

The artifacts are uploaded to the release assets.

### Building for Release

To build all sysroots for a release, use the convenience target:

```bash
cd bazel
# Build all sysroots at once
bazel build //sysroot:sysroots
```

Or build specific glibc versions:

```bash
# Build both variants of all glibc 2.31 sysroots
bazel build //sysroot:sysroot_glibc231_amd64 //sysroot:sysroot_glibc231_arm64 \
  //sysroot:sysroot_glibc231_libstdcxx_amd64 //sysroot:sysroot_glibc231_libstdcxx_arm64

# Build both variants of all glibc 2.28 sysroots
bazel build //sysroot:sysroot_glibc228_amd64 //sysroot:sysroot_glibc228_arm64 \
  //sysroot:sysroot_glibc228_libstdcxx_amd64 //sysroot:sysroot_glibc228_libstdcxx_arm64
```
