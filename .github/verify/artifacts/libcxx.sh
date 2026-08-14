#!/bin/bash
# Verifies darwin libcxx artifact layout and patched install names.
set -euo pipefail

ARTIFACT_DIR="${1:?usage: libcxx.sh <artifact-dir>}"
shopt -s nullglob globstar

matches=("${ARTIFACT_DIR}"/**/libcxx-llvm*-darwin-aarch64.tar.xz)
if [[ "${#matches[@]}" -ne 1 ]]; then
    echo "FAIL: expected 1 darwin libcxx artifact, found ${#matches[@]}"
    exit 1
fi

tarball="${matches[0]}"
listing="$(tar -tvf "${tarball}")"

for path in \
    "include/__config_site" \
    "lib/libc++.1.0.dylib" \
    "lib/libc++.1.dylib" \
    "lib/libc++.dylib" \
    "lib/libc++abi.1.0.dylib" \
    "lib/libc++abi.1.dylib" \
    "lib/libc++abi.dylib"; do
    if ! grep -q " ${path}$" <<< "${listing}"; then
        echo "FAIL: missing ${path} in $(basename "${tarball}")"
        exit 1
    fi
done

if ! grep -q '^l.* lib/libc++.1.dylib -> libc++.1.0.dylib$' <<< "${listing}"; then
    echo "FAIL: libc++.1.dylib symlink missing or incorrect"
    exit 1
fi
if ! grep -q '^l.* lib/libc++.dylib -> libc++.1.0.dylib$' <<< "${listing}"; then
    echo "FAIL: libc++.dylib symlink missing or incorrect"
    exit 1
fi
if ! grep -q '^l.* lib/libc++abi.1.dylib -> libc++abi.1.0.dylib$' <<< "${listing}"; then
    echo "FAIL: libc++abi.1.dylib symlink missing or incorrect"
    exit 1
fi
if ! grep -q '^l.* lib/libc++abi.dylib -> libc++abi.1.0.dylib$' <<< "${listing}"; then
    echo "FAIL: libc++abi.dylib symlink missing or incorrect"
    exit 1
fi

workdir="$(mktemp -d)"
trap 'rm -rf "${workdir}"' EXIT
tar -xf "${tarball}" -C "${workdir}"

if ! strings "${workdir}/lib/libc++.1.0.dylib" | grep -q '/usr/lib/libc++.1.dylib'; then
    echo "FAIL: libc++ install name not patched to /usr/lib/libc++.1.dylib"
    exit 1
fi
if ! strings "${workdir}/lib/libc++abi.1.0.dylib" | grep -q '/usr/lib/libc++abi.dylib'; then
    echo "FAIL: libc++abi install name not patched to /usr/lib/libc++abi.dylib"
    exit 1
fi

echo "PASS: darwin libcxx artifact layout and install names validated"
