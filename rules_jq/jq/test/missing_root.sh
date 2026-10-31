#!/usr/bin/env bash
# Exercise the launcher's module-root failure path in both runfiles layouts.
#
#   $1  rlocationpath of a jq_binary launcher with at least one module dep
#
# Each case must exit non-zero *and* print the diagnostic: a bare `set -e`
# abort inside `$(...)` would exit silently, which is exactly the regression
# this guards against.
set -euo pipefail
source "$TEST_SRCDIR/bazel_tools/tools/bash/runfiles/runfiles.bash"

launcher="$(rlocation "$1")"
runfiles_bash_key=bazel_tools/tools/bash/runfiles/runfiles.bash
runfiles_bash="$(rlocation "$runfiles_bash_key")"
message="jq launcher: cannot resolve module root"

expect_failure() {
    local label="$1"
    shift
    local status=0
    "$@" -n 2> "$TEST_TMPDIR/stderr" || status=$?
    if [[ "$status" == 0 ]]; then
        echo "[$label] expected a nonzero exit status for unresolved module roots" >&2
        exit 1
    fi
    grep -q "$message" "$TEST_TMPDIR/stderr" || {
        echo "[$label] missing error message; stderr was:" >&2
        cat "$TEST_TMPDIR/stderr" >&2
        exit 1
    }
}

# 1. Symlink-tree layout with the module root absent.
empty="$TEST_TMPDIR/empty_runfiles"
mkdir -p "$empty/bazel_tools/tools/bash/runfiles"
cp "$runfiles_bash" "$empty/bazel_tools/tools/bash/runfiles/"
expect_failure "dir" env -u RUNFILES_MANIFEST_FILE RUNFILES_DIR="$empty" "$launcher"

# 2. Manifest layout with the module root absent.
manifest="$TEST_TMPDIR/missing.manifest"
printf '%s %s\n' "$runfiles_bash_key" "$runfiles_bash" > "$manifest"
expect_failure "manifest" env -u RUNFILES_DIR RUNFILES_MANIFEST_FILE="$manifest" "$launcher"
