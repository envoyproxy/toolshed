#!/usr/bin/env bash
set -euo pipefail

out="$(mktemp)"
trap 'rm -f "$out"' EXIT
stderr="$(mktemp)"
trap 'rm -f "$stderr"' EXIT

if "$EXTRACTOR" "$TARBALL" missing deb "$out" 2>"$stderr"; then
    echo "extractor unexpectedly succeeded for missing package" >&2
    cat "$stderr" >&2
    exit 1
fi
grep -Fq -- "expected exactly one missing_*.changes under deb/ in" "$stderr"
