#!/bin/bash
# Tests that the reachability aspect traverses non-standard attribute names
# (e.g. `library`) on custom rules, and that implicit/private (_-prefixed)
# attributes do not contribute recorded edges.

set -euo pipefail

if [ -n "${TEST_SRCDIR:-}" ]; then
    if [ -d "${TEST_SRCDIR}/envoy_toolshed" ]; then
        RUNFILES_DIR="${TEST_SRCDIR}/envoy_toolshed"
    else
        RUNFILES_DIR="${TEST_SRCDIR}/_main"
    fi
    REACHABILITY_JSON="${RUNFILES_DIR}/dependency/test/custom_attr_reachability.json"
else
    echo "This test must be run under Bazel" >&2
    exit 1
fi

JQ="${JQ_BIN:-jq}"

FAILED=0

check() {
    local description="$1"
    local query="$2"
    local expected="$3"
    local actual
    actual="$("${JQ}" -r "${query}" "${REACHABILITY_JSON}")"
    if [ "${actual}" != "${expected}" ]; then
        echo "FAIL: ${description}" >&2
        echo "  query:    ${query}" >&2
        echo "  expected: ${expected}" >&2
        echo "  actual:   ${actual}" >&2
        FAILED=1
    else
        echo "PASS: ${description}"
    fi
}

SKYLIB='.dependencies | to_entries[] | select(.value.name == "bazel_skylib") | .value'

check "bazel_skylib is reported (library attr traversed)" \
    '[.dependencies[] | .name] | unique | join(",")' \
    "bazel_skylib"

check "custom_lib_root reaches bazel_skylib in production" \
    "${SKYLIB} | .production" \
    "true"

check "custom_lib_consumer is recorded as a consumer (library attr edge)" \
    "${SKYLIB} | [.consumers[] | select(.repo == \"\") | .target] | sort | join(\",\")" \
    "//dependency/test:custom_lib_consumer"

check "the external target reached via library attr is recorded" \
    "${SKYLIB} | [.targets[] | sub(\"^@+[^/]*//\"; \"//\")] | sort | join(\",\")" \
    "//lib:shell"

if [ "${FAILED}" -ne 0 ]; then
    exit 1
fi

echo "All tests passed"
