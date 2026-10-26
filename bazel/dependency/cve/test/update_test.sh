#!/usr/bin/env bash
set -euo pipefail

f=bazel_tools/tools/bash/runfiles/runfiles.bash
# shellcheck disable=SC1090
source "${RUNFILES_DIR:-/dev/null}/$f" 2>/dev/null ||
    source "$(grep -sm1 "^$f " "${RUNFILES_MANIFEST_FILE:-/dev/null}" | cut -f2- -d' ')" 2>/dev/null ||
    { echo >&2 "ERROR: cannot find runfiles.bash"; exit 1; }

update="$(rlocation "$UPDATE_SCRIPT")"
fixture_file="$(rlocation "$FIXTURE")"
unset OVERWRITE_ALL_CVE_DATA
"$update" "$TEST_TMPDIR/incremental"
cmp "$fixture_file" "$TEST_TMPDIR/incremental/2024-01.json"
grep -qx -- '--skip' "$TEST_TMPDIR/incremental/args"
grep -qx '2024-01' "$TEST_TMPDIR/incremental/args"
head -n1 "$TEST_TMPDIR/incremental/args" | grep -qx '2024-01'
test -f "$TEST_TMPDIR/incremental/$(date +%Y-%m).json"

OVERWRITE_ALL_CVE_DATA=1 "$update" "$TEST_TMPDIR/overwrite"
test ! -f "$TEST_TMPDIR/overwrite/2024-01.json"
! grep -qx -- '--skip' "$TEST_TMPDIR/overwrite/args"
