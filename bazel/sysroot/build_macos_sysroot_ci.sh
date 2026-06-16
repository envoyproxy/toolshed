#!/usr/bin/env bash

# Build a macOS SDK sysroot tarball for cross-compilation.
# Runs on macOS CI (GitHub Actions macos-14/15 runners have Xcode pre-installed).
#
# Output: sysroot-macos-arm64.tar.xz

set -e -o pipefail

SDK_PATH="${1:-$(xcrun --show-sdk-path --sdk macosx)}"
OUTPUT="${2:-sysroot-macos-arm64.tar.xz}"

if [[ ! -d "$SDK_PATH" ]]; then
    echo "Error: SDK path does not exist: $SDK_PATH"
    exit 1
fi

echo "Building macOS sysroot from: $SDK_PATH"

WORK_DIR=$(mktemp -d)
trap 'rm -rf "$WORK_DIR"' EXIT

SYSROOT="$WORK_DIR/sysroot"
mkdir -p "$SYSROOT"

# System headers
if [[ -d "$SDK_PATH/usr/include" ]]; then
    mkdir -p "$SYSROOT/usr"
    cp -a "$SDK_PATH/usr/include" "$SYSROOT/usr/include"
fi

# Library stubs (.tbd files)
if [[ -d "$SDK_PATH/usr/lib" ]]; then
    mkdir -p "$SYSROOT/usr/lib"
    find "$SDK_PATH/usr/lib" -name "*.tbd" | while read -r f; do
        rel="${f#"$SDK_PATH"/}"
        mkdir -p "$SYSROOT/$(dirname "$rel")"
        cp -a "$f" "$SYSROOT/$rel"
    done
fi

# Frameworks (headers + .tbd stubs)
FRAMEWORKS_DIR="$SDK_PATH/System/Library/Frameworks"
if [[ -d "$FRAMEWORKS_DIR" ]]; then
    mkdir -p "$SYSROOT/System/Library/Frameworks"
    for fw in "$FRAMEWORKS_DIR"/*.framework; do
        fw_name=$(basename "$fw")
        mkdir -p "$SYSROOT/System/Library/Frameworks/$fw_name"
        # Copy the entire framework structure (Headers, Modules, .tbd, Versions/)
        # preserving the layout so clang can find versioned headers.
        find "$fw" \( -name "Headers" -type d -o -name "Modules" -type d -o -name "*.tbd" \) | while IFS= read -r item; do
            rel="${item#"$SDK_PATH"/}"
            mkdir -p "$(dirname "$SYSROOT/$rel")"
            cp -a "$item" "$SYSROOT/$rel"
        done
    done
fi

# SDK settings
for f in SDKSettings.json SDKSettings.plist; do
    [[ -f "$SDK_PATH/$f" ]] && cp -a "$SDK_PATH/$f" "$SYSROOT/"
done

echo "Packaging sysroot..."
tar -cJf "$OUTPUT" -C "$SYSROOT" .

SIZE=$(du -sh "$OUTPUT" | cut -f1)
SHA=$(shasum -a 256 "$OUTPUT" | cut -d' ' -f1)
echo ""
echo "Built: $OUTPUT ($SIZE)"
echo "SHA256: $SHA"
