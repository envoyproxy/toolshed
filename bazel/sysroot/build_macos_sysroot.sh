#!/usr/bin/env bash

# Build a macOS SDK sysroot tarball for cross-compilation from Linux.
#
# Usage (on macOS):
#   ./build_macos_sysroot.sh [--sdk-path /path/to/MacOSX.sdk] [--output sysroot-macos.tar.xz]
#
# The default SDK path is detected via `xcrun --show-sdk-path`.
# Output is a tarball suitable for use with the `macos_sysroot` Bazel repository rule.

set -e -o pipefail

SDK_PATH=""
OUTPUT="sysroot-macos-arm64.tar.xz"

usage() {
    echo "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "  --sdk-path PATH   Path to MacOSX.sdk (default: auto-detect via xcrun)"
    echo "  --output FILE     Output tarball path (default: sysroot-macos-arm64.tar.xz)"
    echo ""
    echo "Examples:"
    echo "  # Auto-detect SDK on macOS"
    echo "  $0"
    echo ""
    echo "  # Use a specific SDK"
    echo "  $0 --sdk-path /Library/Developer/CommandLineTools/SDKs/MacOSX15.0.sdk"
    echo ""
    echo "  # Extract from Xcode"
    echo "  $0 --sdk-path /Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk"
    exit 1
}

while [[ $# -gt 0 ]]; do
    case $1 in
        --sdk-path)
            SDK_PATH="$2"
            shift 2
            ;;
        --output)
            OUTPUT="$2"
            shift 2
            ;;
        --help|-h)
            usage
            ;;
        *)
            echo "Unknown option: $1"
            usage
            ;;
    esac
done

if [[ -z "$SDK_PATH" ]]; then
    if command -v xcrun &>/dev/null; then
        SDK_PATH=$(xcrun --show-sdk-path --sdk macosx)
        echo "Auto-detected SDK: $SDK_PATH"
    else
        echo "Error: --sdk-path required (xcrun not available)"
        exit 1
    fi
fi

if [[ ! -d "$SDK_PATH" ]]; then
    echo "Error: SDK path does not exist: $SDK_PATH"
    exit 1
fi

if [[ ! -f "$SDK_PATH/SDKSettings.json" ]] && [[ ! -f "$SDK_PATH/SDKSettings.plist" ]]; then
    echo "Error: $SDK_PATH does not look like a macOS SDK (no SDKSettings found)"
    exit 1
fi

echo "Building macOS sysroot from: $SDK_PATH"
echo "Output: $OUTPUT"

WORK_DIR=$(mktemp -d)
trap 'rm -rf "$WORK_DIR"' EXIT

SYSROOT="$WORK_DIR/sysroot"
mkdir -p "$SYSROOT"

echo "Copying SDK headers..."
# System headers
if [[ -d "$SDK_PATH/usr/include" ]]; then
    mkdir -p "$SYSROOT/usr"
    cp -a "$SDK_PATH/usr/include" "$SYSROOT/usr/include"
fi

echo "Copying library stubs (.tbd files)..."
# Library stubs — .tbd files are text-based stubs that tell the linker about symbols
if [[ -d "$SDK_PATH/usr/lib" ]]; then
    mkdir -p "$SYSROOT/usr/lib"
    find "$SDK_PATH/usr/lib" -name "*.tbd" -exec cp --parents -a {} "$SYSROOT/" \; 2>/dev/null || \
    find "$SDK_PATH/usr/lib" -name "*.tbd" | while read -r f; do
        rel="${f#"$SDK_PATH"/}"
        mkdir -p "$SYSROOT/$(dirname "$rel")"
        cp -a "$f" "$SYSROOT/$rel"
    done
fi

echo "Copying frameworks..."
# Frameworks — headers and .tbd stubs
FRAMEWORKS_DIR="$SDK_PATH/System/Library/Frameworks"
if [[ -d "$FRAMEWORKS_DIR" ]]; then
    mkdir -p "$SYSROOT/System/Library/Frameworks"
    for fw in "$FRAMEWORKS_DIR"/*.framework; do
        fw_name=$(basename "$fw")
        mkdir -p "$SYSROOT/System/Library/Frameworks/$fw_name"
        # Copy headers
        if [[ -d "$fw/Headers" ]]; then
            cp -a "$fw/Headers" "$SYSROOT/System/Library/Frameworks/$fw_name/"
        fi
        # Copy Modules (for module maps)
        if [[ -d "$fw/Modules" ]]; then
            cp -a "$fw/Modules" "$SYSROOT/System/Library/Frameworks/$fw_name/"
        fi
        # Copy .tbd files
        find "$fw" -maxdepth 1 -name "*.tbd" -exec cp -a {} "$SYSROOT/System/Library/Frameworks/$fw_name/" \; 2>/dev/null || true
        # Copy versioned .tbd files
        if [[ -d "$fw/Versions" ]]; then
            find "$fw/Versions" -name "*.tbd" | while read -r f; do
                rel="${f#"$SDK_PATH"/}"
                mkdir -p "$SYSROOT/$(dirname "$rel")"
                cp -a "$f" "$SYSROOT/$rel"
            done
        fi
    done
fi

# SDK settings
for f in SDKSettings.json SDKSettings.plist; do
    if [[ -f "$SDK_PATH/$f" ]]; then
        cp -a "$SDK_PATH/$f" "$SYSROOT/"
    fi
done

echo "Packaging sysroot..."
tar -cJf "$OUTPUT" -C "$SYSROOT" .

SIZE=$(du -sh "$OUTPUT" | cut -f1)
echo ""
echo "Successfully built macOS sysroot: $OUTPUT ($SIZE)"
echo "SHA256: $(sha256sum "$OUTPUT" | cut -d' ' -f1 2>/dev/null || shasum -a 256 "$OUTPUT" | cut -d' ' -f1)"
