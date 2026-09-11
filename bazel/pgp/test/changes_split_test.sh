#!/usr/bin/env bash
set -euo pipefail

for distro in a b; do
    output="${!distro}"
    expected="$(mktemp)"
    trap 'rm -f "$expected"' EXIT
    sed "s/^Distribution:.*/Distribution: ${distro}/" "$INPUT" > "$expected"
    cmp "$expected" "$output"
done
