#!/usr/bin/env bash

# Build darwin arm64 libc++ cross-compilation libraries from an LLVM release.
#
# This produces a tarball containing:
#   include/__config_site   — darwin-specific libc++ configuration
#   lib/libc++.1.dylib      — libc++ dynamic library for darwin arm64
#   lib/libc++abi.1.0.dylib — libc++abi dynamic library for darwin arm64
#
# Requirements:
#   - A macOS SDK sysroot (from build_macos_sysroot.sh or Xcode)
#   - cmake, ninja
#   - clang with darwin target support (the hermetic LLVM works)
#
# Usage:
#   ./build_libcxx_darwin.sh \
#     --llvm-source /path/to/llvm-project-source \
#     --sysroot /path/to/macos-sdk-sysroot \
#     --clang /path/to/clang \
#     --output libcxx-darwin-arm64.tar.xz

set -e -o pipefail

LLVM_SOURCE=""
SYSROOT=""
CLANG=""
OUTPUT="libcxx-darwin-arm64.tar.xz"

usage() {
    echo "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "  --llvm-source DIR   Path to LLVM monorepo source (containing libcxx/, libcxxabi/)"
    echo "  --sysroot DIR       Path to macOS SDK sysroot"
    echo "  --clang PATH        Path to clang binary (must support --target=aarch64-apple-macosx)"
    echo "  --output FILE       Output tarball (default: libcxx-darwin-arm64.tar.xz)"
    exit 1
}

while [[ $# -gt 0 ]]; do
    case $1 in
        --llvm-source) LLVM_SOURCE="$2"; shift 2 ;;
        --sysroot) SYSROOT="$2"; shift 2 ;;
        --clang) CLANG="$2"; shift 2 ;;
        --output) OUTPUT="$2"; shift 2 ;;
        --help|-h) usage ;;
        *) echo "Unknown option: $1"; usage ;;
    esac
done

if [[ -z "$LLVM_SOURCE" ]] || [[ -z "$SYSROOT" ]] || [[ -z "$CLANG" ]]; then
    echo "Error: --llvm-source, --sysroot, and --clang are required"
    usage
fi

WORK_DIR=$(mktemp -d)
trap 'rm -rf "$WORK_DIR"' EXIT

BUILD_DIR="$WORK_DIR/build"
INSTALL_DIR="$WORK_DIR/install"
mkdir -p "$BUILD_DIR" "$INSTALL_DIR/include" "$INSTALL_DIR/lib"

TARGET="aarch64-apple-macosx"

echo "Building libc++ for darwin arm64..."
echo "  LLVM source: $LLVM_SOURCE"
echo "  Sysroot: $SYSROOT"
echo "  Clang: $CLANG"

cmake -G Ninja -S "$LLVM_SOURCE/runtimes" -B "$BUILD_DIR" \
    -DCMAKE_C_COMPILER="$CLANG" \
    -DCMAKE_CXX_COMPILER="$CLANG++" \
    -DCMAKE_C_COMPILER_TARGET="$TARGET" \
    -DCMAKE_CXX_COMPILER_TARGET="$TARGET" \
    -DCMAKE_SYSTEM_NAME=Darwin \
    -DCMAKE_SYSTEM_PROCESSOR=arm64 \
    -DCMAKE_OSX_ARCHITECTURES=arm64 \
    -DCMAKE_SYSROOT="$SYSROOT" \
    -DCMAKE_INSTALL_PREFIX="$INSTALL_DIR" \
    -DLLVM_ENABLE_RUNTIMES="libcxx;libcxxabi;libunwind" \
    -DLIBCXX_ENABLE_SHARED=ON \
    -DLIBCXX_ENABLE_STATIC=OFF \
    -DLIBCXXABI_ENABLE_SHARED=ON \
    -DLIBCXXABI_ENABLE_STATIC=OFF \
    -DLIBCXX_CXX_ABI=libcxxabi \
    -DLIBCXXABI_USE_LLVM_UNWINDER=ON \
    -DLIBCXX_USE_COMPILER_RT=ON \
    -DLIBCXXABI_USE_COMPILER_RT=ON \
    -DCMAKE_BUILD_TYPE=Release

ninja -C "$BUILD_DIR" install-cxx install-cxxabi

echo "Packaging..."
STAGING="$WORK_DIR/staging"
mkdir -p "$STAGING/include" "$STAGING/lib"

cp "$INSTALL_DIR/include/c++/v1/__config_site" "$STAGING/include/"
find "$INSTALL_DIR/lib" -name "libc++*.dylib" -exec cp -a {} "$STAGING/lib/" \;

tar -cJf "$OUTPUT" -C "$STAGING" .
SIZE=$(du -sh "$OUTPUT" | cut -f1)
echo ""
echo "Built: $OUTPUT ($SIZE)"
echo "SHA256: $(sha256sum "$OUTPUT" 2>/dev/null | cut -d' ' -f1 || shasum -a 256 "$OUTPUT" | cut -d' ' -f1)"
