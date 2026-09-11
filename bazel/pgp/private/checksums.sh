#!/usr/bin/env bash
#
# Generate a `shasum`-format checksums file.
#
#   checksums.sh <algorithm> <out> <input>...
#
# Checksums are emitted with the basename of each input, matching the
# `sha256sum`/`shasum` output format used by the toolshed gpg actions.

set -euo pipefail

if [[ $# -lt 3 ]]; then
    echo "usage: $0 ALGORITHM OUT INPUT..." >&2
    exit 2
fi

ALGORITHM="$1"
OUT="$2"
shift 2

case "$ALGORITHM" in
    sha256|sha512)
        ;;
    *)
        echo "unknown algorithm: ${ALGORITHM}" >&2
        exit 2
        ;;
esac

BITS="${ALGORITHM#sha}"

checksum () {
    local file="$1"
    if command -v "${ALGORITHM}sum" > /dev/null 2>&1; then
        "${ALGORITHM}sum" "$file"
    elif command -v shasum > /dev/null 2>&1; then
        shasum -a "$BITS" "$file"
    else
        echo "no ${ALGORITHM} implementation found" >&2
        exit 1
    fi
}

: > "$OUT"

for input in "$@"; do
    (
        cd "$(dirname "$input")"
        checksum "$(basename "$input")"
    ) >> "$OUT"
done
