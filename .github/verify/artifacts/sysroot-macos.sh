#!/bin/bash
# Verifies macOS sysroot artifact layout.
set -euo pipefail

ARTIFACT_DIR="${1:?usage: sysroot-macos.sh <artifact-dir>}"
shopt -s nullglob globstar

matches=("${ARTIFACT_DIR}"/**/sysroot-macos-arm64.tar.xz)
if [[ "${#matches[@]}" -ne 1 ]]; then
    echo "FAIL: expected 1 macOS sysroot artifact, found ${#matches[@]}"
    exit 1
fi

tarball="${matches[0]}"
listing="$(tar -tf "${tarball}")"

for path in \
    "macos_arm64/usr/include/" \
    "macos_arm64/usr/lib/libc.tbd" \
    "macos_arm64/usr/lib/libSystem.tbd" \
    "macos_arm64/System/Library/Frameworks/CoreFoundation.framework/" \
    "macos_arm64/System/Library/Frameworks/Foundation.framework/" \
    "macos_arm64/System/Library/Frameworks/Security.framework/"; do
    if ! grep -q "^${path}" <<< "${listing}"; then
        echo "FAIL: expected path '${path}' not found in $(basename "${tarball}")"
        exit 1
    fi
done

echo "PASS: macOS sysroot artifact layout validated"
