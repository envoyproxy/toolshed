#!/usr/bin/env bash
# Usage: check_reports <OUTPUT> [REPORT...]
# Fails if any clang-tidy --export-fixes report contains diagnostics, otherwise
# creates OUTPUT.
set -euo pipefail

OUTPUT=$1
shift

failed=false
for report in "$@"; do
    # run_clang_tidy.sh leaves the report empty when clang-tidy finds nothing.
    if [[ ! -s "$report" ]]; then
        continue
    fi

    diagnostics=$(grep -m1 '^Diagnostics:' "$report" || true)
    if [[ "$diagnostics" == "Diagnostics: []" ]]; then
        continue
    fi

    if [[ -z "$diagnostics" ]]; then
        echo "Malformed clang-tidy report has no Diagnostics field: $report" >&2
    else
        echo "clang-tidy found diagnostics in $report:" >&2
    fi
    cat "$report" >&2
    failed=true
done

if [[ "$failed" == true ]]; then
    exit 1
fi

touch "$OUTPUT"
