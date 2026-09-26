#!/bin/bash

set -euo pipefail

src="$1"
resolved="$(cat "$2")"
prefix="$3"
out="$4"

prefix_re="$(printf '%s' "$prefix" | sed -e 's/[][(){}.^$*+?|\\]/\\&/g')"
pattern="^([A-Za-z0-9_:-]* --registry=)${prefix_re}/[0-9a-f]+[[:space:]]*$"

if ! grep -qE "$pattern" "$src"; then
    echo "No '--registry=${prefix}/<sha>' line found in ${src}" >&2
    exit 1
fi

sed -E "s#${pattern}#\\1${resolved}#" "$src" > "$out"
