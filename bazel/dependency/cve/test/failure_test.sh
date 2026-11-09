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
grep -q "Source: NVD" "$TEST_TMPDIR/report"
grep -q "Source: CVE Program (example)" "$TEST_TMPDIR/report"
grep -q "CVE-2024-0006" "$TEST_TMPDIR/report"
grep -q "NVD: not analyzed (no CPE data)" "$TEST_TMPDIR/report"
grep -q "Affected: Example/Widget 1.0 <= v < 1.3 affected" "$TEST_TMPDIR/report"
grep -q "2 potential CVE vulnerabilities found" "$TEST_TMPDIR/report"
grep -q "(0 NVD only, 1 CVE Program only, 1 both)" "$TEST_TMPDIR/report"

# A scan that cannot be read fails the test, rather than passing it
echo "not json" > "$TEST_TMPDIR/broken.json"
status=0
SCANNED="$TEST_TMPDIR/broken.json" "$(rlocation "$CVE_TEST")" > "$TEST_TMPDIR/broken" 2>&1 || status=$?
[[ "$status" -ne 0 ]]
if grep -q "potential CVE" "$TEST_TMPDIR/broken"; then
    exit 1
fi

status=0
"$(rlocation "$EMPTY_SCAN")" > "$TEST_TMPDIR/empty" 2>&1 || status=$?
[[ "$status" -eq 1 ]]
grep -q "No CVE data set" "$TEST_TMPDIR/empty"
