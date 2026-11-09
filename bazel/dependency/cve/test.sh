#!/usr/bin/env bash
set -euo pipefail

f=bazel_tools/tools/bash/runfiles/runfiles.bash
# shellcheck disable=SC1090
source "${RUNFILES_DIR:-/dev/null}/$f" 2>/dev/null ||
    source "$(grep -sm1 "^$f " "${RUNFILES_MANIFEST_FILE:-/dev/null}" | cut -f2- -d' ')" 2>/dev/null ||
    source "$0.runfiles/$f" 2>/dev/null ||
    { echo >&2 "ERROR: cannot find runfiles.bash"; exit 1; }

JQ_BIN="$(rlocation "$JQ_BIN")"
JQ_REPORT="$(rlocation "$JQ_REPORT")"
SCANNED="$(rlocation "$SCANNED")"

# A plain assignment, so that a jq failure aborts under `set -e` rather than
# comparing as zero and passing the test.
count="$("$JQ_BIN" 'length' "$SCANNED")"
if [[ "$count" -gt 0 ]]; then
    "$JQ_BIN" -r -f "$JQ_REPORT" "$SCANNED"
    exit 1
fi
