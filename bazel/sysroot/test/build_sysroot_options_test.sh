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

# Removed options must not be advertised, and base builds must remain available.
output=$(bash "$script" 2>&1) && {
    echo "Expected missing required arguments to fail" >&2
    exit 1
}
for option in --variant --ppa-toolchain --stdcc; do
    if [[ "$output" == *"$option"* ]]; then
        echo "Removed option $option is still advertised" >&2
        exit 1
    fi
done
for option in --arch --glibc --debian; do
    if [[ "$output" != *"$option"* ]]; then
        echo "Missing base sysroot option $option" >&2
        exit 1
    fi
done
