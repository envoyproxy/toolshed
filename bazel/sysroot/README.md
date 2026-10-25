# Sysroots

This directory contains both sysroot repository rules for downloading pre-built sysroots and build targets for creating new sysroots.

## Available Sysroots

The workflow builds sysroots with the following configurations:

### glibc 2.31 (Current)
- **Base:** Debian bullseye
- **Compatibility:** Modern Linux distributions
- **Kernel Headers:** 5.10+ (from bullseye-backports)
- **Archive:** `sysroot-glibc2.31-{arch}.tar.xz`

### glibc 2.28 (Older)
- **Base:** Debian buster
- **Compatibility:** Ubuntu 18.04, RHEL 8, and older distributions
- **Kernel Headers:** 5.10+ (from buster-backports)
- **Archive:** `sysroot-glibc2.28-{arch}.tar.xz`

Each sysroot includes the `libgcc_s.so.1` runtime and an unversioned
`usr/lib/<triple>/libgcc_s.so` linker script so literal `-lgcc_s` links resolve
(needed by, for example, rustc). It does not include `libgcc.a` or libstdc++;
Clang consumers should use `-rtlib=compiler-rt`. C++ standard-library headers and
libraries must come from the selected toolchain, not the sysroot.

### GCC and LLVM share the base sysroot

`--config=gcc` selects hermetic GCC 13.4.0; `--config=rbe-gcc` retains the
existing remote execution platforms. Both GCC target architectures execute on
Linux x86_64 (including aarch64 cross-compilation). GCC supplies its own
libstdc++, libgcc, libgcc_eh, and crtbegin/crtend objects; glibc supplies
crt1/crti/crtn from this sysroot. GCC links its C++ runtime statically.
LLVM continues to supply compiler-rt and libc++ from its own toolchain.

The pinned archives come from
[f0rmiga/gcc-builds release 18082025](https://github.com/f0rmiga/gcc-builds/releases/tag/18082025),
the same source used by envoyproxy/envoy#39632. Its
[build recipe](https://github.com/f0rmiga/gcc-builds/blob/3fcca92fd993788a88af150cd4c885e4860e0055/Dockerfile)
builds the target runtime against glibc 2.26. The repository rule removes the
archive's bundled libc sysroot and explicitly uses toolshed's glibc 2.31 sysroot.
Replacement GCC archives **must build their target runtimes against glibc
<= 2.31**; changing `--sysroot` cannot lower the glibc requirement of an
already-built libstdc++.

Downstreams can instantiate the downloads with `gcc_extension` from
`//toolchains/gcc:extensions.bzl`, using a `toolchain(name = ..., arch =
"x86_64" | "aarch64", sysroot = "@sysroot_linux_...//sysroot")` tag per target.
Each generated repository exports `:cc_toolchain`, `:config`, and `:files`.
The sysroot label must point directly into the `sysroot` package, not its
root-package alias.

**Release TODO:** the next `bins-v*` release must regenerate both wee8
libstdcxx archives and refresh `VERSIONS["wee8_sha256"][arch]["libstdcxx"]`
before downstream consumption (including envoyproxy/envoy#39632). Existing
x86_64 libstdcxx artifacts were built against host glibc 2.39 and are not
compatible with this floor; aarch64 libstdcxx remains an incompatible prebuilt
stub until its first archive/hash is published. `//v8:wee8_packages` builds
all four arch/stdlib combinations without consuming these prebuilts.

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
`sysroot_hashes[glibc_version][arch]`.

### Migrating existing configurations

Sysroots no longer bundle libstdc++. Remove `stdcc_version` from repository-rule,
`setup_sysroots`, and module-extension calls, and remove `variant`, `ppa_toolchain`,
and `stdcc_version` arguments from `sysrootfs` calls. The script no longer accepts
`--variant`, `--ppa-toolchain`, or `--stdcc`. Use the unsuffixed sysroot build
targets below and supply any C++ standard library through the toolchain.
Existing unsuffixed archives and their SHA256 hashes are unchanged.

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
bazel build //sysroot:sysroot_glibc228_amd64
bazel build //sysroot:sysroot_glibc228_arm64
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
# Build all glibc 2.31 sysroots
bazel build //sysroot:sysroot_glibc231_amd64 //sysroot:sysroot_glibc231_arm64

# Build all glibc 2.28 sysroots
bazel build //sysroot:sysroot_glibc228_amd64 //sysroot:sysroot_glibc228_arm64
```
