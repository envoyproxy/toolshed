#!/usr/bin/env bash
#
# Regression guard for the signer source itself.
#
# A process substitution inside an array assignment creates an fd that bash
# closes again once the assignment completes, so the array cannot carry it to
# the command that eventually consumes it (this broke `--password-file` under
# the Bazel sandbox). Assert that the signer never does that, and shellcheck
# the script when a `shellcheck` is available.

set -euo pipefail

SIGNER="${SIGNER:-pgp/private/signer.sh}"
if [[ ! -f "$SIGNER" ]]; then
    SIGNER="$(dirname "$0")/../private/signer.sh"
fi

if [[ ! -f "$SIGNER" ]]; then
    echo "signer script not found" >&2
    exit 1
fi

failed=0

# Tracks array assignments (`foo=(` / `foo+=(`) across lines and fails if a
# `<(` appears before the assignment is closed.
if ! awk '
    {
        line = $0
        sub(/[[:space:]]*#.*$/, "", line)
        if (!in_array && line ~ /^[[:space:]]*[A-Za-z_][A-Za-z_0-9]*\+?=\(/) {
            in_array = 1
            start = NR
        }
        if (in_array) {
            if (index(line, "<(")) {
                printf "%s:%d: process substitution inside array assignment started at line %d\n", FILENAME, NR, start
                bad = 1
            }
            n = gsub(/\(/, "(", line) - gsub(/\)/, ")", line)
            depth += n
            if (depth <= 0) {
                in_array = 0
                depth = 0
            }
        }
    }
    END {exit bad}' "$SIGNER"; then
    echo "FAIL: process substitution used inside an array assignment" >&2
    failed=1
else
    echo "ok: no process substitution inside array assignments"
fi

SHELLCHECK="${SHELLCHECK:-$(command -v shellcheck || true)}"
if [[ -n "$SHELLCHECK" ]]; then
    if "$SHELLCHECK" "$SIGNER"; then
        echo "ok: shellcheck clean"
    else
        echo "FAIL: shellcheck reported issues" >&2
        failed=1
    fi
else
    echo "note: no shellcheck available, source is linted in CI"
fi

if [[ "$failed" -ne 0 ]]; then
    exit 1
fi

echo "signer source test passed"
