#!/usr/bin/env bash
set -euo pipefail
source "$TEST_SRCDIR/bazel_tools/tools/bash/runfiles/runfiles.bash"
status=0
"$(rlocation "$1")" -e -n || status=$?
if [[ "$status" != 1 ]]; then
    echo "Expected false to produce a nonzero exit status" >&2
    exit 1
fi
