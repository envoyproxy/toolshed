# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

`envoyproxy/toolshed` is a multi-language CI and development tooling monorepo for the Envoy proxy project. It contains Python packages (published to PyPI), Bazel build rules (published to the Bazel Central Registry), Rust binaries, TypeScript GitHub Actions, shell scripts, and jq modules.

## Build systems

The repo uses **two parallel build systems** covering different areas:

- **Pants** — manages all Python packages under `py/`
- **Bazel** — manages build rules, C++ compile targets, and integration; all Bazel commands run from the `bazel/` subdirectory

Pants explicitly ignores the `bazel/` directory; Bazel does not manage Python packages.

## Common commands

### Python (Pants)

`pants` is already on PATH — do **not** run `./get-pants.sh`.

```bash
# Run all tests
pants test ::

# Run tests for a single package
pants test envoy.dependency.check::

# Filter tests by name
pants test --debug envoy.dependency.check:: -- -k checker_cves

# Coverage report
pants test --open-coverage ::

# Lint (flake8 + docformatter)
pants lint ::

# Type-check (mypy)
pants check ::

# Package (wheel)
pants package ::
```

### Bazel

All Bazel commands must run from the `bazel/` directory.

```bash
cd bazel

bazel build //...
bazel test //...
bazel test --config=ci //...        # CI-style, suppressed progress
bazel build --enable_bzlmod //...   # bzlmod mode (default is WORKSPACE mode)
bazel build --config=gcc //...      # GCC toolchain
```

The `.bazelrc` disables bzlmod by default (`--noenable_bzlmod`). The Bazel module is `envoy_toolshed` version `0.3.32-dev`.

### Rust (from `rust/`)

```bash
cd rust
cargo build --release -p glint
cargo build --release -p toolshed-echo
cargo tarpaulin --config tarpaulin.toml --features test --lib --bins   # coverage
cargo test --package glint --test integration_test --verbose
```

### JavaScript (per-package from `js/<pkg>/`)

```bash
cd js/<package-name>
npm ci --legacy-peer-deps
npm run lint
npm test
npm run build
```

### Global lint (shell, yaml, glint)

```bash
envoy.code.check . -c glint shellcheck yamllint
```

### V8 wee8 static library

```bash
# Local build (no RBE) — takes 30–120 min cold
cd bazel
bazel build -c opt --enable_bzlmod --noenable_workspace //v8:wee8_package_linux_x86_64

# Cross-compile for aarch64 from an x86_64 machine
bazel build -c opt --enable_bzlmod --noenable_workspace \
    --platforms=@toolchains_llvm//platforms:linux-aarch64 \
    //v8:wee8_package_linux_aarch64

# Quick Starlark syntax check
bazel query --enable_bzlmod --noenable_workspace //v8:wee8_package_linux_x86_64
```

Output tarballs land in `bazel-bin/v8/v8-wee8-{version}-linux-{arch}.tar.xz`.

CI (`package-v8` in `bazel.yml`) builds both arches on `ubuntu-24.04` (x86_64) with RBE.
The aarch64 build cross-compiles via `--platforms=@toolchains_llvm//platforms:linux-aarch64`.
A native arm64 runner was tried but abandoned: V8's `code_generator` exec tool (a Python venv)
fails on aarch64 exec platforms due to a venv bootstrap issue.

## Architecture

### Python packages (`py/`)

Two namespaces:
- **`aio.*`** — generic async libraries (not Envoy-specific): core utilities, run framework, checker framework
- **`envoy.*`** — Envoy-specific runners and checkers: dependency CVE checking, code linting, release management, GitHub automation, distribution verification

All packages are async-first (`asyncio`). Two runnable archetypes:
- **Runners** — run a series of steps, exit on failure
- **Checkers** — run a series of checks, accumulate errors/warnings/successes

Packages are consumed by Envoy via `rules_python` from PyPI. To test changes locally in an Envoy environment without publishing, add an editable path reference to Envoy's `tools/dev/requirements.txt`:
```
-e file:///path/to/toolshed/py/envoy.dependency.check#egg=envoy.dependency.check&cachebust=000
```
Increment `cachebust` on each change to bust Bazel's cache.

### Bazel rules (`bazel/`)

Reusable Starlark rules for:
- C++ compilation with LLVM 18.x toolchains (`bazel/compile/` — MSAN/TSAN sanitizer libraries, libcxx cross-compile bundles)
- Debian sysroot generation for cross-compilation (`bazel/sysroot/`)
- Envoy website Python dependency targets (`bazel/website/`)
- V8 wee8 prebuilt library distribution (`bazel/v8/`)

A local BCR is maintained in `bazel-registry/` for publishing `envoy_toolshed` to the Bazel Central Registry.

### V8 wee8 prebuilt library (`bazel/v8/`) — **IN PROGRESS** 🚧

**Purpose:** Provide prebuilt V8 wee8 static libraries (`libwee8.a`) to eliminate 30-120 minute V8 build times for Envoy and other consumers.

**Status (as of 2026-08-18):** Infrastructure 95% complete, blocked on transitive dependencies issue.

**Completed Steps:**
1. ✅ **Artifact build pipeline** — PR #5019 merged (Aug 13, 2026)
2. ✅ **bins-v0.2.8 release** — Published (Aug 14, 2026) with 3 wee8 tarballs:
   - `v8-wee8-14.6.202.10-linux-x86_64.tar.xz` (libcxx, 15.2 MB)
   - `v8-wee8-14.6.202.10-linux-x86_64-libstdcxx.tar.xz` (libstdc++, 15.2 MB)
   - `v8-wee8-14.6.202.10-linux-aarch64.tar.xz` (libcxx, 14.4 MB)
3. ✅ **Release automation** — wee8 SHA propagation in bazel prepare workflow (PRs #5043, #5047)
4. ✅ **Bazel module v0.4.6** — Published (Aug 16, 2026) with V8 infrastructure
5. ✅ **Post-merge improvements** — PRs #5050, #5052, #5053, #5066 (hermetic builds, multi-stdlib, platform selection, tests)
6. ✅ **Envoy integration branch** — `manage-wee8-library` created with setup_wee8_prebuilt() configured

**Current V8 version:** `14.6.202.10` (in `bazel/versions.bzl`)

**Current Blocker:**

`@proxy_wasm_cpp_host//:v8_lib` compiles `src/v8/v8.cc` which includes abseil headers (e.g., `absl/strings/str_format.h`). The original `@v8//:wee8` target provided these as transitive dependencies, but our prebuilt wee8 BUILD template doesn't include any deps.

**Error:**
```
external/proxy_wasm_cpp_host/src/v8/v8.cc:33:10: fatal error: 'absl/strings/str_format.h' file not found
```

**Two Paths Forward:**

**Path A: Fix toolshed BUILD template** (cleaner, recommended)
1. Update `_WEE8_BUILD` in `bazel/v8/wee8_prebuilt.bzl` to add deps:
   ```python
   cc_library(
       name = "wee8",
       srcs = ["lib/libwee8.a"],
       hdrs = [":headers"],
       includes = [".", "include"],
       linkstatic = True,
       deps = [
           "@abseil-cpp//absl/strings:str_format",
           "@abseil-cpp//absl/container:flat_hash_map",
           "@abseil-cpp//absl/container:flat_hash_set",
           "@abseil-cpp//absl/container:btree",
           # Add other V8 transitive deps as needed
       ],
   )
   ```
2. Cut toolshed v0.4.7 release
3. Update Envoy's `repository_locations.bzl` to use v0.4.7
4. Complete Envoy integration

**Path B: Patch proxy_wasm v8_lib** (faster, but messier)
1. Extend `bazel/proxy_wasm_cpp_host.patch` to add abseil deps directly to the `v8_lib` target
2. Works with current toolshed v0.4.6
3. Less clean - puts dependency knowledge in wrong place

**Current Envoy branch state (`manage-wee8-library`):**
- ✅ `setup_wee8_prebuilt()` configured in `bazel/repositories_extra.bzl`
- ✅ `bazel/proxy_wasm_cpp_host.patch` updated to alias wee8_no_pointer_compression
- ✅ V8 BUILD patched via `patch_cmds` to use prebuilt (avoids patch file format issues)
- ❌ Blocked on missing abseil deps compilation error

**What's available:**

**For WORKSPACE consumers (Envoy):**
```python
# In bazel/repositories_extra.bzl
load("@envoy_toolshed//v8:wee8_prebuilt.bzl", "setup_wee8_prebuilt")

def envoy_dependencies_extra(...):
    setup_wee8_prebuilt()  # Creates @wee8_prebuilt_* repos
```

**For bzlmod consumers:**
```python
# In MODULE.bazel
bazel_dep(name = "envoy_toolshed", version = "0.4.6.envoy")  # When available in BCR

# Use the platform-agnostic alias
deps = ["@envoy_toolshed//v8:wee8"]
```

**Platform selection** (automatic via `@envoy_toolshed//v8:wee8` alias):
- Linux x86_64 + Clang → `@wee8_prebuilt_x86_64//:wee8` (libcxx)
- Linux x86_64 + GCC → `@wee8_prebuilt_x86_64_libstdcxx//:wee8` (libstdc++)
- Linux aarch64 + Clang → `@wee8_prebuilt_aarch64//:wee8` (libcxx)
- Other platforms → `@v8//:wee8` (fallback: build from source)

**Key files:**
- `bazel/v8/wee8_package.bzl` — Build rule for creating prebuilt tarballs
- `bazel/v8/wee8_prebuilt.bzl` — Repository rules for consuming prebuilts (`setup_wee8_prebuilt()`)
- `bazel/v8/extensions.bzl` — bzlmod module extension (`wee8_prebuilt_extension`)
- `bazel/v8/BUILD` — Platform-agnostic `//v8:wee8` alias
- `bazel/v8/package/BUILD` — Packaging targets for CI
- `bazel/versions.bzl` — `V8_VERSION = "14.6.202.10"` and `wee8_sha256` hashes

**Next Steps:**
1. **Immediate:** Add abseil deps to `_WEE8_BUILD` template in toolshed
2. Cut toolshed v0.4.7 release
3. Update Envoy to v0.4.7 and complete integration testing
4. Open Envoy PR for wee8 prebuilt integration
5. Open bazel-registry PR for envoy_toolshed@0.4.6.envoy (or 0.4.7)

**Build time savings (when complete):** 30-120 minutes → seconds

**When bumping V8 version:**
1. Update `V8_VERSION` in `bazel/versions.bzl`
2. Update `bazel_dep(name = "v8", version = "...")` in `bazel/MODULE.bazel`
3. Cut a new bins release (wee8 SHAs auto-update in bazel prepare workflow)
4. Cut a new bazel module release

**Local testing with unpublished tarball:**
```bash
export V8_PREBUILT_PATH=/path/to/dir/containing/tarball
```

### Rust (`rust/`)

Cargo workspace with members: `core`, `echo`, `glint`, `runner`, `test`.
- `glint` — the primary linting binary used in global CI lint checks
- `toolshed-echo` — an echo server binary

### JavaScript/TypeScript (`js/`)

Nine composite GitHub Actions built with TypeScript + `ncc`:
`appauth`, `dispatch`, `github/checks`, `github/mutex`, `github/script/run`, `hashfiles`, `jq`, `retest`, `torun`.

## Python coding standards

- Python 3.12 required (`>=3.12,<3.13`)
- All code must be type-hinted; mypy must pass
- Async-first: use `asyncio` patterns throughout
- Use `breakpoint()` (not `print`) for debugging; `pants test --debug` drops into pdb

## CI

GitHub Actions workflows are path-filtered so each language area only triggers on its relevant files. Key workflows: `py.yml` (Python), `bazel.yml` (Bazel), `rust.yml` (Rust), `js.yml` (JavaScript), `lint.yml` (global lint on every PR).
