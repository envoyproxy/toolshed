#!/usr/bin/env bash
set -euo pipefail

"$SQ" --batch --home none --cert-store none --key-store none inspect "$PUBLIC_KEY"

assert_fails() {
    local input="$1"
    local message="$2"
    if "$VALIDATOR" "$input" "$TMP/output" > "$TMP/stderr" 2>&1; then
        echo "validator unexpectedly accepted $input" >&2
        exit 1
    fi
    grep -Fq -- "$message" "$TMP/stderr"
}

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
assert_fails "$SECRET_KEY" "PRIVATE KEY"
assert_fails "$NOT_A_KEY" "missing public key block"
