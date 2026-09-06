#!/usr/bin/env bash
#
# Exercises `audit_test.sh` against captured `bazel aquery` output.
#
# `fixtures/audit.json` is the real aquery output for the example signing
# targets in this package and must pass. The `audit-*.json` fixtures each
# break one of the guarantees (a removed execution requirement, a leaked
# environment variable, key material as an action input, a passphrase on the
# command line) and must be rejected - this is the negative test for the
# audit itself.

set -euo pipefail

AUDIT="$(dirname "$0")/audit_test.sh"
FIXTURES="$(dirname "$0")/fixtures"
PASSPHRASE="correct-horse-battery-staple"

if [[ ! -x "$AUDIT" ]]; then
    AUDIT="bash ${AUDIT}"
fi

failed=0

audit () {
    $AUDIT --forbid "$PASSPHRASE" --aquery-json "$1"
}

echo "# audit passes for compliant actions"
if ! audit "${FIXTURES}/audit.json"; then
    echo "FAIL: audit rejected compliant actions" >&2
    failed=1
fi

for fixture in "${FIXTURES}"/audit-*.json; do
    echo "# audit fails for $(basename "$fixture")"
    if audit "$fixture"; then
        echo "FAIL: audit accepted $(basename "$fixture")" >&2
        failed=1
    fi
done

if [[ "$failed" -ne 0 ]]; then
    exit 1
fi

echo "audit fixtures test passed"
