#!/usr/bin/env bash

set -euo pipefail

validator="$1"
fixtures="$(dirname "$2")"
output="${TEST_TMPDIR}/validate-output"
for fixture in pass overall_fail per_dir_fail adjustable no_validation; do
    for mode in default summary; do
        args=("$fixtures/$fixture.json")
        [[ "$mode" != summary ]] || args+=(--summary-only)
        expected=0
        if [[ "$fixture" == overall_fail || ( "$fixture" == per_dir_fail && "$mode" == default ) ]]; then
            expected=1
        fi
        status=0
        "$validator" "${args[@]}" >"$output" || status=$?
        [[ "$status" == "$expected" ]]
        if [[ "$mode" == default && ( "$fixture" == per_dir_fail || "$fixture" == adjustable ) ]]; then
            grep -qx "DIRECTORY REPORT" "$output"
        else
            grep -qx "OVERALL SUMMARY" "$output"
        fi
    done
done
if "$validator" "$fixtures/missing.json" >"$output" 2>&1; then
    echo "Expected missing report to fail" >&2
    exit 1
fi
