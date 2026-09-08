#!/usr/bin/env bash
set -euo pipefail

cmp "$EXTRACTED" "$INPUT"

contrib="$(mktemp)"
trap 'rm -f "$contrib"' EXIT
sed 's/^Source:.*/Source: example-contrib/' "$INPUT" > "$contrib"

if cmp -s "$EXTRACTED" "$contrib"; then
    echo "extracted changes unexpectedly matches example-contrib content" >&2
    exit 1
fi
