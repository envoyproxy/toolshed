#!/usr/bin/env bash
# A jq_binary without main or filter takes the program and flags from its
# arguments, with its libraries importable.
set -euo pipefail
source "$TEST_SRCDIR/bazel_tools/tools/bash/runfiles/runfiles.bash"
jq="$(rlocation "$1")"
# `$who` is a jq variable, not a shell one.
# shellcheck disable=SC2016
program='import "greet" as greet; $who | greet::hello'

check() {
    [[ "$1" == "Hello world" ]] || {
        echo "$2: expected 'Hello world', got '$1'" >&2
        exit 1
    }
}

check "$("$jq" -n -r --arg who ' world ' "$program")" "runfiles env"

# Run by path from inside this test's runfiles tree, with no runfiles env, as a
# `bazel run` script calling it by `$(rootpath)` does.
if [[ "$jq" == *.runfiles/* ]]; then
    check "$(env -u RUNFILES_DIR -u RUNFILES_MANIFEST_FILE "$jq" -n -r --arg who ' world ' "$program")" "inside a runfiles tree"
fi
