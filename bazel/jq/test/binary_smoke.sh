#!/usr/bin/env bash
set -euo pipefail
source "$TEST_SRCDIR/bazel_tools/tools/bash/runfiles/runfiles.bash"
"$(rlocation "$1")" "$(rlocation "$2")" > "$TEST_TMPDIR/actual"
diff -u "$(rlocation "$3")" "$TEST_TMPDIR/actual"
