#!/bin/bash

set -euo pipefail

if [ -n "${TEST_SRCDIR:-}" ]; then
    if [ -d "${TEST_SRCDIR}/envoy_toolshed" ]; then
        RUNFILES_DIR="${TEST_SRCDIR}/envoy_toolshed"
    else
        RUNFILES_DIR="${TEST_SRCDIR}/_main"
    fi
    REWRITE_SCRIPT="${RUNFILES_DIR}/dependency/registry_bazelrc.sh"
    SOURCE_BAZELRC="${RUNFILES_DIR}/dependency/test/testdata/registry.missing.bazelrc"
    RESOLVED_REGISTRY="${RUNFILES_DIR}/dependency/test/testdata/resolved.txt"
else
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    REWRITE_SCRIPT="$(cd "${SCRIPT_DIR}/.." && pwd)/registry_bazelrc.sh"
    SOURCE_BAZELRC="${SCRIPT_DIR}/testdata/registry.missing.bazelrc"
    RESOLVED_REGISTRY="${SCRIPT_DIR}/testdata/resolved.txt"
fi

OUTPUT="$(mktemp)"
trap 'rm -f "${OUTPUT}"' EXIT

if bash "${REWRITE_SCRIPT}" \
    "${SOURCE_BAZELRC}" \
    "${RESOLVED_REGISTRY}" \
    "https://raw.githubusercontent.com/envoyproxy/bazel-registry" \
    "${OUTPUT}" >"${OUTPUT}.stdout" 2>"${OUTPUT}.stderr"; then
    echo "registry_bazelrc.sh unexpectedly succeeded"
    exit 1
fi

grep -F "No '--registry=https://raw.githubusercontent.com/envoyproxy/bazel-registry/<sha>' line found" "${OUTPUT}.stderr" >/dev/null
