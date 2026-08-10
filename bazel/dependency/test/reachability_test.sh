#!/bin/bash
# Test for the dependency_reachability rule/aspect: verifies that the emitted
# JSON reachability map attributes external repositories to the surfaces and
# consumers that reach them, including testonly/production tracking.

set -euo pipefail

# ---------------------------------------------------------------------------
# Locate runfiles when running under Bazel
# ---------------------------------------------------------------------------
if [ -n "${TEST_SRCDIR:-}" ]; then
    if [ -d "${TEST_SRCDIR}/envoy_toolshed" ]; then
        RUNFILES_DIR="${TEST_SRCDIR}/envoy_toolshed"
    else
        RUNFILES_DIR="${TEST_SRCDIR}/_main"
    fi
    REACHABILITY_JSON="${RUNFILES_DIR}/dependency/test/reachability.json"
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

# The canonical repo name for bazel_skylib differs between WORKSPACE
# ("bazel_skylib") and bzlmod ("bazel_skylib+"/"bazel_skylib~") builds, so
# select entries via the emitted apparent name.
SKYLIB='.dependencies | to_entries[] | select(.value.name == "bazel_skylib") | .value'

check "bazel_skylib is the only reported dependency" \
    '[.dependencies[] | .name] | unique | join(",")' \
    "bazel_skylib"

check "a non-testonly path to bazel_skylib exists" \
    "${SKYLIB} | .production" \
    "true"

check "both roots reach bazel_skylib" \
    "${SKYLIB} | [.reached_by[].root] | sort | join(\",\")" \
    "//dependency/test:core_root,//dependency/test:test_root"

check "core root reaches bazel_skylib in production" \
    "${SKYLIB} | .reached_by[] | select(.root == \"//dependency/test:core_root\") | \"\(.root) \(.production)\"" \
    "//dependency/test:core_root true"

check "test root only reaches bazel_skylib via testonly paths" \
    "${SKYLIB} | .reached_by[] | select(.root == \"//dependency/test:test_root\") | \"\(.root) \(.production)\"" \
    "//dependency/test:test_root false"

check "consumed external targets are recorded" \
    "${SKYLIB} | [.targets[] | sub(\"^@+[^/]*//\"; \"//\")] | sort | join(\",\")" \
    "//lib:paths,//lib:sets"

check "in-repo consumers are recorded with testonly attribution" \
    "${SKYLIB} | [.consumers[] | select(.repo == \"\") | \"\(.target) \(.testonly)\"] | sort | join(\",\")" \
    "//dependency/test:external_consumer false,//dependency/test:test_root true"

check "shared consumer is attributed to both roots" \
    "${SKYLIB} | .consumers[] | select(.target == \"//dependency/test:external_consumer\") | .roots | sort | join(\",\")" \
    "//dependency/test:core_root,//dependency/test:test_root"

check "testonly consumer is only attributed to the test root" \
    "${SKYLIB} | .consumers[] | select(.target == \"//dependency/test:test_root\") | .roots | join(\",\")" \
    "//dependency/test:test_root"

if [ "${FAILED}" -ne 0 ]; then
    exit 1
fi

echo "All tests passed"
