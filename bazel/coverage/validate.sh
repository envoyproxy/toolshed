#!/usr/bin/env bash

set -euo pipefail

# --- begin runfiles.bash initialization v2 ---
f=bazel_tools/tools/bash/runfiles/runfiles.bash
# shellcheck disable=SC1090
source "${RUNFILES_DIR:-/dev/null}/$f" 2>/dev/null || \
    source "$(grep -sm1 "^$f " "${RUNFILES_MANIFEST_FILE:-/dev/null}" | cut -f2- -d' ')" 2>/dev/null || \
    source "$0.runfiles/$f" 2>/dev/null || \
    source "$(grep -sm1 "^$f " "$0.runfiles_manifest" | cut -f2- -d' ')" 2>/dev/null || \
    { echo >&2 "ERROR: cannot find runfiles.bash"; exit 1; }
# --- end runfiles.bash initialization v2 ---

if [[ $# -lt 1 || $# -gt 2 || ( $# -eq 2 && "$2" != --summary-only ) ]]; then
    echo "Usage: $0 coverage.json [--summary-only]" >&2
    exit 1
fi
COVERAGE_JSON="$1"
if [[ "$COVERAGE_JSON" != /* && -n "${BUILD_WORKING_DIRECTORY:-}" ]]; then
    COVERAGE_JSON="$BUILD_WORKING_DIRECTORY/$COVERAGE_JSON"
fi
if [[ ! -f "$COVERAGE_JSON" ]]; then
    echo "ERROR: Coverage JSON file not found: $COVERAGE_JSON" >&2
    exit 1
fi
if ! JQ_BIN="$(rlocation "${JQ_BIN:-}")" ||
    ! COVERAGE_CONFIG="$(rlocation "${COVERAGE_CONFIG:-}")" ||
    [[ ! -x "$JQ_BIN" || ! -f "$COVERAGE_CONFIG" ]]; then
    echo "ERROR: Coverage jq binary or configuration not found in runfiles" >&2
    exit 1
fi

if [[ "${2:-}" == --summary-only ]]; then
    "$JQ_BIN" -r '.summary_message' "$COVERAGE_JSON"
    "$JQ_BIN" -e '.summary.threshold_reached != false' "$COVERAGE_JSON" >/dev/null
else
    "$JQ_BIN" -r '
        if ((.validation_summary.failed_count // 0) > 0
            or (.validation_summary.adjustable_count // 0) > 0)
        then .summary_report else .summary_message end' "$COVERAGE_JSON"
    "$JQ_BIN" -e '
        (.validation_summary.failed_count // 0) == 0
        and .summary.threshold_reached != false' "$COVERAGE_JSON" >/dev/null
fi
