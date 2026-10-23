#!/usr/bin/env bash
set -euo pipefail

f=bazel_tools/tools/bash/runfiles/runfiles.bash
# shellcheck disable=SC1090
source "${RUNFILES_DIR:-/dev/null}/$f" 2>/dev/null ||
    source "$(grep -sm1 "^$f " "${RUNFILES_MANIFEST_FILE:-/dev/null}" | cut -f2- -d' ')" 2>/dev/null ||
    source "$0.runfiles/$f" 2>/dev/null ||
    { echo >&2 "ERROR: cannot find runfiles.bash"; exit 1; }

JQ_BIN="$(rlocation "$JQ_BIN")"
TOOLSHED_JQ_ROOT="$(rlocation "$TOOLSHED_JQ_ROOT")"
CPE_DEPS="$(rlocation "$CPE_DEPS")"
CVES_IGNORED="$(rlocation "$CVES_IGNORED")"
JQ_CVE_MATCHER="$(rlocation "$JQ_CVE_MATCHER")"
CVE_FILES="$(rlocation "$CVE_FILES")"

files=()
while IFS= read -r file; do
    files+=("$(rlocation "$file")")
done < "$CVE_FILES"
if [[ ${#files[@]} -eq 0 ]]; then
    echo >&2 "No CVE data set"
    exit 1
fi

"$JQ_BIN" -L "$(dirname "$TOOLSHED_JQ_ROOT")" -f "$JQ_CVE_MATCHER" \
    --slurpfile deps "$CPE_DEPS" --slurpfile ignored "$CVES_IGNORED" "${files[@]}" |
    "$JQ_BIN" -s '[.[][]]'
