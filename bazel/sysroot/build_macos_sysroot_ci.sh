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

# Frameworks — copy entire directory. SDK frameworks contain only headers,
# modules, .tbd stubs, and symlinks (no large binaries). Preserving the
# complete structure is essential because clang's framework header lookup
# depends on symlinks like Headers -> Versions/Current/Headers.
if [[ -d "$SDK_PATH/System/Library/Frameworks" ]]; then
    mkdir -p "$SYSROOT/System/Library"
    cp -a "$SDK_PATH/System/Library/Frameworks" "$SYSROOT/System/Library/"
fi

# SDK settings
for f in SDKSettings.json SDKSettings.plist; do
    [[ -f "$SDK_PATH/$f" ]] && cp -a "$SDK_PATH/$f" "$SYSROOT/"
done

# Remove circular symlinks (e.g., Ruby.framework/Versions/2.6/Headers/ruby/ruby -> .)
echo "Removing circular symlinks..."
find "$SYSROOT" -type l | while read -r link; do
    target=$(readlink "$link")
    if [[ "$target" == "." || "$target" == ".." ]]; then
        rm "$link"
    fi
done

echo "Packaging sysroot..."
tar -cJf "$OUTPUT" -C "$SYSROOT" .

SIZE=$(du -sh "$OUTPUT" | cut -f1)
SHA=$(shasum -a 256 "$OUTPUT" | cut -d' ' -f1)
echo ""
echo "Built: $OUTPUT ($SIZE)"
echo "SHA256: $SHA"
