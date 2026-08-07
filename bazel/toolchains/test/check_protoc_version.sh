#!/usr/bin/env bash
# Verifies that a file contains the expected libprotoc major.minor version.
# Usage: check_protoc_version.sh <version_file> <expected_version>
set -euo pipefail

VERSION_FILE="${1:?Usage: $0 <version_file> <expected_version>}"
EXPECTED="${2:?Usage: $0 <version_file> <expected_version>}"

if [[ ! -f "${VERSION_FILE}" ]]; then
    echo "ERROR: version file not found: ${VERSION_FILE}" >&2
    exit 1
fi

ACTUAL="$(cat "${VERSION_FILE}")"
echo "protoc --version output: ${ACTUAL}"

if grep -qF "${EXPECTED}" "${VERSION_FILE}"; then
    echo "OK: found expected version '${EXPECTED}'"
else
    echo "FAIL: expected '${EXPECTED}' not found in output: ${ACTUAL}" >&2
    exit 1
fi
