#!/bin/bash
set -euo pipefail

: "${SQ:?SQ must be set}"
: "${SQ_VERSION:?SQ_VERSION must be set}"
: "${REPO_NAME_FILE:?REPO_NAME_FILE must be set}"

version="$("$SQ" version 2>&1 || true)"
test "${version%%$'\n'*}" = "sq $SQ_VERSION"
grep -q 'sq_toolchains' "$REPO_NAME_FILE"
echo "PASS: sq toolchain version checks passed"
