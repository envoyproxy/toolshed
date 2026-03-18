#!/usr/bin/env bash

# Script to build V8's wee8 static library and package it for distribution.
#
# This script uses the self-contained Bazel workspace in bazel/v8/build/ which
# has all V8 dependencies pinned. It does NOT depend on the Envoy repository.
#
# Usage:
#   ./build_v8.sh [--arch x86_64] [--output-dir /tmp/v8-out] [--bazel-opts "..."]
#
# The resulting tarball can be uploaded to GitHub releases for consumption by
# the v8_prebuilt repository rule.

set -e -o pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUILD_DIR="$SCRIPT_DIR/build"
ARCH="x86_64"
OUTPUT_DIR="/tmp/v8-prebuilt"
BAZEL_BUILD_OPTS=""

usage() {
    echo "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "  --arch           Target architecture (x86_64 or aarch64, default: x86_64)"
    echo "  --output-dir     Output directory for the tarball (default: /tmp/v8-prebuilt)"
    echo "  --bazel-opts     Additional Bazel build options"
    echo ""
    exit 1
}

while [[ $# -gt 0 ]]; do
    case $1 in
        --arch)
            ARCH="$2"
            shift 2
            ;;
        --output-dir)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        --bazel-opts)
            BAZEL_BUILD_OPTS="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            usage
            ;;
    esac
done

if [[ ! -f "$BUILD_DIR/WORKSPACE" ]]; then
    echo "Error: Cannot find $BUILD_DIR/WORKSPACE"
    echo "This script must be run from the envoy_toolshed repository."
    exit 1
fi

# Extract V8 version from the WORKSPACE file
V8_VERSION=$(grep '^V8_VERSION' "$BUILD_DIR/WORKSPACE" | sed 's/.*"\(.*\)".*/\1/')
if [[ -z "$V8_VERSION" ]]; then
    echo "Error: Could not determine V8 version from $BUILD_DIR/WORKSPACE"
    exit 1
fi

echo "Building V8 wee8 library:"
echo "  V8 version: $V8_VERSION"
echo "  Architecture: $ARCH"
echo "  Build dir: $BUILD_DIR"
echo "  Output dir: $OUTPUT_DIR"
echo ""

WORK_DIR=$(mktemp -d)
trap 'rm -rf "$WORK_DIR"' EXIT

# Step 1: Build V8's wee8 target using the self-contained build workspace
echo "Step 1: Building @v8//:wee8 ..."
cd "$BUILD_DIR"
# shellcheck disable=SC2086
bazel build -c opt @v8//:wee8 $BAZEL_BUILD_OPTS

# Step 2: Collect all .o files from V8 and its V8-specific dependencies
echo ""
echo "Step 2: Collecting object files ..."

BAZEL_BIN=$(bazel info -c opt output_path)/k8-opt/bin
BAZEL_EXTERNAL="$BAZEL_BIN/external"

# Bazel puts compiled objects in _objs/ subdirectories, not in .a archives.
# Collect .o files from V8 and V8-specific deps (NOT abseil-cpp or llvm_toolchain).
ALL_OBJECTS=()
for dep_dir in v8 dragonbox fast_float fp16 simdutf highway; do
    if [[ -d "$BAZEL_EXTERNAL/$dep_dir" ]]; then
        while IFS= read -r -d '' obj; do
            ALL_OBJECTS+=("$obj")
        done < <(find "$BAZEL_EXTERNAL/$dep_dir" -name '*.pic.o' -print0)
    fi
done

if [[ ${#ALL_OBJECTS[@]} -eq 0 ]]; then
    echo "Error: No object files found. Build may have failed."
    exit 1
fi

echo "  Found ${#ALL_OBJECTS[@]} object files"

# Step 3: Create a single static library from all object files
echo ""
echo "Step 3: Creating libwee8.a ..."

STAGING_DIR="$WORK_DIR/staging"
mkdir -p "$STAGING_DIR/lib" "$STAGING_DIR/include"

ar rcs "$STAGING_DIR/lib/libwee8.a" "${ALL_OBJECTS[@]}"
echo "  Created libwee8.a ($(du -h "$STAGING_DIR/lib/libwee8.a" | cut -f1))"

# Step 4: Copy headers
echo ""
echo "Step 4: Copying headers ..."

V8_EXTERNAL_SRC=$(bazel info output_base)/external/v8

# Copy all V8 public API headers (needed by proxy_wasm_cpp_host and other consumers)
cp -r "$V8_EXTERNAL_SRC/include" "$STAGING_DIR/"

# Copy wasm-api headers at both locations:
# - include/ for direct #include "wasm.h" usage
# - third_party/wasm-api/ for V8 internal #include "third_party/wasm-api/wasm.hh"
cp "$V8_EXTERNAL_SRC/third_party/wasm-api/wasm.h" "$STAGING_DIR/include/"
cp "$V8_EXTERNAL_SRC/third_party/wasm-api/wasm.hh" "$STAGING_DIR/include/"
mkdir -p "$STAGING_DIR/third_party/wasm-api"
cp "$V8_EXTERNAL_SRC/third_party/wasm-api/wasm.h" "$STAGING_DIR/third_party/wasm-api/"
cp "$V8_EXTERNAL_SRC/third_party/wasm-api/wasm.hh" "$STAGING_DIR/third_party/wasm-api/"

# Copy V8 internal headers required by proxy_wasm_cpp_host (src/wasm/c-api.h
# and its transitive includes). Uses a Python script to resolve the dependency
# tree and copy only what's needed.
python3 -c "
import re, os, shutil, sys
v8_root = sys.argv[1]
staging = sys.argv[2]
visited = set()
queue = ['src/wasm/c-api.h']
while queue:
    f = queue.pop(0)
    if f in visited:
        continue
    visited.add(f)
    src = os.path.join(v8_root, f)
    if not os.path.exists(src):
        continue
    dst = os.path.join(staging, f)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copy2(src, dst)
    with open(src) as fh:
        for line in fh:
            m = re.match(r'#include\s+\"(src/[^\"]+)\"', line)
            if m:
                queue.append(m.group(1))
print('  Copied %d internal V8 headers (src/)' % len(visited))
" "$V8_EXTERNAL_SRC" "$STAGING_DIR"

HEADER_COUNT=$(find "$STAGING_DIR/include" "$STAGING_DIR/src" "$STAGING_DIR/third_party" -name '*.h' -o -name '*.hh' 2>/dev/null | wc -l)
echo "  Total headers: $HEADER_COUNT"

# Step 5: Package
echo ""
echo "Step 5: Packaging ..."

mkdir -p "$OUTPUT_DIR"
TARBALL="$OUTPUT_DIR/v8-wee8-${V8_VERSION}-linux-${ARCH}.tar.xz"

cd "$STAGING_DIR"
tar -cJf "$TARBALL" lib/ include/ src/ third_party/

echo "  Created: $TARBALL"
echo "  Size: $(du -h "$TARBALL" | cut -f1)"
echo ""
echo "SHA256: $(sha256sum "$TARBALL" | cut -d' ' -f1)"
echo ""
echo "Done!"
