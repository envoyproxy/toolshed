#!/bin/bash

set -euo pipefail

: "${RESOLVED:?RESOLVED must be set}"
: "${JQ_BIN:?JQ_BIN must be set}"

resolved_path="${RESOLVED}"
if [ ! -f "${resolved_path}" ] && [ -n "${TEST_SRCDIR:-}" ]; then
    if [ -d "${TEST_SRCDIR}/envoy_toolshed" ]; then
        resolved_path="${TEST_SRCDIR}/envoy_toolshed/${RESOLVED}"
    else
        resolved_path="${TEST_SRCDIR}/_main/${RESOLVED}"
    fi
fi

if [ ! -f "${resolved_path}" ]; then
    echo "resolved registry output not found: ${resolved_path}" >&2
    exit 1
fi

"${JQ_BIN}" -e '.url | test("^https://raw\\.githubusercontent\\.com/envoyproxy/bazel-registry/[0-9a-f]{40}$")' "${resolved_path}" >/dev/null
