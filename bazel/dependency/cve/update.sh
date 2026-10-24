#!/usr/bin/env bash
set -euo pipefail

f=bazel_tools/tools/bash/runfiles/runfiles.bash
# shellcheck disable=SC1090
source "${RUNFILES_DIR:-/dev/null}/$f" 2>/dev/null ||
    source "$(grep -sm1 "^$f " "${RUNFILES_MANIFEST_FILE:-/dev/null}" | cut -f2- -d' ')" 2>/dev/null ||
    source "$0.runfiles/$f" 2>/dev/null ||
    { echo >&2 "ERROR: cannot find runfiles.bash"; exit 1; }

START_YEAR_PATH="$(rlocation "$START_YEAR_PATH")"
FETCHER="$(rlocation "$FETCHER")"
CVE_FILES="$(rlocation "$CVE_FILES")"
output="$1"
mkdir -p "$output"
start_year="$(cat "$START_YEAR_PATH")"
current_month="$(date +%Y-%m)"
skip=()

while IFS= read -r file; do
    month="$(basename "$file" .json)"
    if [[ ! "$month" =~ ^[0-9]{4}-(0[1-9]|1[0-2])$ ]]; then
        echo >&2 "Expected a YYYY-MM.json CVE data file: $file"
        exit 1
    fi
    if [[ -z "${OVERWRITE_ALL_CVE_DATA:-}" && "$month" != "$current_month" ]]; then
        cp "$(rlocation "$file")" "$output/$month.json"
        skip+=("$month")
    fi
done < "$CVE_FILES"

args=(--output_path="$output" --overwrite)
if [[ ${#skip[@]} -gt 0 ]]; then
    months="$(IFS=,; echo "${skip[*]}")"
    args+=(--skip "$months")
fi
"$FETCHER" "${start_year}-01" "$current_month" "${args[@]}"
