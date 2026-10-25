#!/usr/bin/env bash

set -euo pipefail

script="$1"
for option in --variant --ppa-toolchain --stdcc; do
    if output=$(bash "$script" "$option" obsolete 2>&1); then
        echo "Expected removed option $option to fail" >&2
        exit 1
    fi
    if [[ "$output" != "Unknown option: $option"$'\n'* ]]; then
        echo "Expected an unknown-option error for $option, got: $output" >&2
        exit 1
    fi
done
