#!/usr/bin/env bash
set -euo pipefail

f=bazel_tools/tools/bash/runfiles/runfiles.bash
# shellcheck disable=SC1090
source "${RUNFILES_DIR:-/dev/null}/$f" 2>/dev/null ||
    source "$(grep -sm1 "^$f " "${RUNFILES_MANIFEST_FILE:-/dev/null}" | cut -f2- -d' ')" 2>/dev/null ||
    { echo >&2 "ERROR: cannot find runfiles.bash"; exit 1; }

JQ_BIN="$(rlocation "$JQ_BIN")"
SCANNED="$(rlocation "$SCANNED")"

actual="$("$JQ_BIN" -c 'map([.id, .sources, (.matched | map(.source))])' "$SCANNED")"
if [[ "$actual" != "$EXPECTED" ]]; then
    echo >&2 "expected: $EXPECTED"
    echo >&2 "actual:   $actual"
    exit 1
fi
