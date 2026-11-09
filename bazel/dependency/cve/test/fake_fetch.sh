#!/usr/bin/env bash
set -euo pipefail

for arg in "$@"; do
    if [[ "$arg" == --output_path=* ]]; then
        output="${arg#--output_path=}"
    fi
done
printf '%s\n' "$@" > "$output/args"
printf '{"vulnerabilities":[]}\n' > "$output/$(date +%Y-%m).json"
