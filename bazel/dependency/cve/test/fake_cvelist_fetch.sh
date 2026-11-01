#!/usr/bin/env bash
set -euo pipefail

for arg in "$@"; do
    if [[ "$arg" == --output_path=* ]]; then
        output="${arg#--output_path=}"
    fi
done
mkdir -p "$output"
printf '%s\n' "$@" > "$output/args"
printf '{"records":[]}\n' > "$output/$(date +%Y-%m).json"
