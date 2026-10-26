#!/usr/bin/env bash
set -euo pipefail

f=bazel_tools/tools/bash/runfiles/runfiles.bash
# shellcheck disable=SC1090
source "${RUNFILES_DIR:-/dev/null}/$f" 2>/dev/null ||
    source "$(grep -sm1 "^$f " "${RUNFILES_MANIFEST_FILE:-/dev/null}" | cut -f2- -d' ')" 2>/dev/null ||
    { echo >&2 "ERROR: cannot find runfiles.bash"; exit 1; }

status=0
"$(rlocation "$CVE_TEST")" > "$TEST_TMPDIR/report" 2>&1 || status=$?
[[ "$status" -eq 1 ]]
grep -q "CVE-2024-0001" "$TEST_TMPDIR/report"
grep -q "widget" "$TEST_TMPDIR/report"
grep -q "1 potential CVE vulnerabilities found" "$TEST_TMPDIR/report"

status=0
"$(rlocation "$EMPTY_SCAN")" > "$TEST_TMPDIR/empty" 2>&1 || status=$?
[[ "$status" -eq 1 ]]
grep -q "No CVE data set" "$TEST_TMPDIR/empty"
