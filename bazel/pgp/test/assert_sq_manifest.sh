#!/bin/bash
set -euo pipefail

: "${TAR:?TAR must be set}"
: "${TARBALL:?TARBALL must be set}"
: "${READELF:?READELF must be set}"
: "${SQ_VERSION:?SQ_VERSION must be set}"

TAR="$(realpath "$TAR")"

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
"$TAR" -xf "$TARBALL" -C "$tmp"
sq=$(find "$tmp" -path '*/bin/sq' -type f -print -quit)
test -n "$sq"
version=$("$sq" version 2>&1 || true)
test "${version%%$'\n'*}" = "sq $SQ_VERSION"
if "$READELF" -d "$sq" | grep -Eq 'NEEDED.*(libssl|libsqlite3|libcrypto)'; then
    echo "sq unexpectedly links to OpenSSL or SQLite" >&2
    exit 1
fi
echo "PASS: sq manifest checks passed"
