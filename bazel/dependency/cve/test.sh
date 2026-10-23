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
JQ_REPORT="$(rlocation "$JQ_REPORT")"
SCANNED="$(rlocation "$SCANNED")"

if [[ $("$JQ_BIN" 'length' "$SCANNED") -gt 0 ]]; then
    "$JQ_BIN" -r -L "$(dirname "$TOOLSHED_JQ_ROOT")" -f "$JQ_REPORT" "$SCANNED"
    exit 1
fi
