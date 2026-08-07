#!/usr/bin/env bash
# Verifies that a file contains the expected libprotoc major.minor version.
# VERSION_FILE: path to the file with protoc --version output (env var or $1)
# EXPECTED_PROTOC_VERSION: expected string, e.g. "libprotoc 35.1" (env var or $2)
set -euo pipefail

VERSION_FILE="${VERSION_FILE:-${1:?VERSION_FILE env var or first arg required}}"
EXPECTED="${EXPECTED_PROTOC_VERSION:-${2:?EXPECTED_PROTOC_VERSION env var or second arg required}}"

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
