#!/usr/bin/env bash
set -euo pipefail

tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
passphrase='correct-horse-battery-staple'
printf '%s\n' "$passphrase" > "$tmp/passphrase"

"$AUDIT" --forbid-file "$tmp/passphrase" --aquery-json "$AQUERY" > "$tmp/clean" 2>&1

if "$AUDIT" --forbid-file "$tmp/passphrase" --aquery-json "$AQUERY_BROKEN" \
        > "$tmp/report" 2>&1; then
    echo "audit unexpectedly accepted forbidden file contents" >&2
    exit 1
fi
grep -Fq -- "--forbid-file $tmp/passphrase" "$tmp/report"
! grep -Fq -- "$passphrase" "$tmp/report"
