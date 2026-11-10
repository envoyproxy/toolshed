#!/usr/bin/env bash
# Stand-in for lcov-merge with the same CLI: `--output <file> <tracefile>...`. It records
# its arguments and concatenates the inputs, which is a valid (if unmerged) tracefile that
# grcov merges itself, so the report generator's wiring is exercised without the binary.
set -euo pipefail
output=
inputs=()
while [[ $# -gt 0 ]]; do
    case "$1" in
        --output) output="$2"; shift ;;
        --output=*) output="${1#*=}" ;;
        *) inputs+=("$1") ;;
    esac
    shift
done
[[ -n "$output" ]] || { echo "fake lcov-merge: --output is required" >&2; exit 1; }
[[ ${#inputs[@]} -gt 0 ]] || { echo "fake lcov-merge: no inputs" >&2; exit 1; }
if [[ -n "${FAKE_LCOV_MERGE_LOG:-}" ]]; then
    printf '%s\n' "${inputs[@]}" > "$FAKE_LCOV_MERGE_LOG"
fi
cat "${inputs[@]}" > "$output"
