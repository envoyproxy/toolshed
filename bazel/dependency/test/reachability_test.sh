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
    REACHABILITY_ATTRIBUTION_JSON="${RUNFILES_DIR}/dependency/test/reachability_attribution.json"
    REACHABILITY_ATTRIBUTION_MULTICONFIG_JSON="${RUNFILES_DIR}/dependency/test/reachability_attribution_multiconfig.json"
    REACHABILITY_EMPTY_ATTRIBUTION_PATTERNS_JSON="${RUNFILES_DIR}/dependency/test/reachability_empty_attribution_patterns.json"
    REACHABILITY_MULTICONFIG_JSON="${RUNFILES_DIR}/dependency/test/reachability_multiconfig.json"
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
    local file="${4:-${REACHABILITY_JSON}}"
    local actual
    actual="$("${JQ}" -r "${query}" "${file}")"
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
JQ_TOOLCHAINS='.dependencies | to_entries[] | select(.value.name == "jq_toolchains") | .value'

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

if ! cmp -s "${REACHABILITY_JSON}" "${REACHABILITY_EMPTY_ATTRIBUTION_PATTERNS_JSON}"; then
    echo "FAIL: explicit empty attribution patterns must be byte-identical to defaults" >&2
    FAILED=1
else
    echo "PASS: explicit empty attribution patterns must be byte-identical to defaults"
fi

check "shared consumer is attributed to both roots" \
    "${SKYLIB} | .consumers[] | select(.target == \"//dependency/test:external_consumer\") | .roots | sort | join(\",\")" \
    "//dependency/test:core_root,//dependency/test:test_root"

check "testonly consumer is only attributed to the test root" \
    "${SKYLIB} | .consumers[] | select(.target == \"//dependency/test:test_root\") | .roots | join(\",\")" \
    "//dependency/test:test_root"

check "multi-config bazel_skylib records all configs" \
    "${SKYLIB} | .configs | sort | join(\",\")" \
    "default,extra" \
    "${REACHABILITY_MULTICONFIG_JSON}"

check "multi-config bazel_skylib remains production because one root is non-testonly" \
    "${SKYLIB} | .production" \
    "true" \
    "${REACHABILITY_MULTICONFIG_JSON}"

check "multi-config bazel_skylib reached_by preserves both roots with unioned production" \
    "${SKYLIB} | [.reached_by[] | \"\(.root) \(.production)\"] | sort | join(\",\")" \
    "//dependency/test:variant_core_root true,//dependency/test:variant_test_root false" \
    "${REACHABILITY_MULTICONFIG_JSON}"

check "multi-config bazel_skylib testonly root remains scoped to that root" \
    "${SKYLIB} | .consumers[] | select(.target == \"//dependency/test:variant_test_root\") | .roots | sort | join(\",\")" \
    "//dependency/test:variant_test_root" \
    "${REACHABILITY_MULTICONFIG_JSON}"

check "config-gated jq_toolchains dependency appears in merged output" \
    "${JQ_TOOLCHAINS} | .name" \
    "jq_toolchains" \
    "${REACHABILITY_MULTICONFIG_JSON}"

check "config-gated jq_toolchains dependency is attributed to extra only" \
    "${JQ_TOOLCHAINS} | .configs | join(\",\")" \
    "extra" \
    "${REACHABILITY_MULTICONFIG_JSON}"

check "config-gated jq_toolchains dependency tracks only the root and consumer that reach it" \
    "${JQ_TOOLCHAINS} | [.consumers[] | \"\(.target) \(.testonly) \(.roots | sort | join(\"|\"))\"] | sort | join(\",\")" \
    "//dependency/test:variant_external_consumer false //dependency/test:variant_core_root|//dependency/test:variant_test_root" \
    "${REACHABILITY_MULTICONFIG_JSON}"

check "config-gated jq_toolchains consumer attrs are recorded and unioned across configs" \
    "${JQ_TOOLCHAINS} | .consumers[] | select(.target == \"//dependency/test:variant_external_consumer\") | .attrs | join(\",\")" \
    "srcs" \
    "${REACHABILITY_MULTICONFIG_JSON}"

check "multi-config bazel_skylib consumer attrs are recorded" \
    "${SKYLIB} | .consumers[] | select(.target == \"//dependency/test:variant_external_consumer\") | .attrs | join(\",\")" \
    "srcs" \
    "${REACHABILITY_MULTICONFIG_JSON}"

check "transitive attribution includes extension-like packages through shared intermediates" \
    "${SKYLIB} | [.attributed_packages[].package] | sort | join(\",\")" \
    "//dependency/test/transitive/ext/deep,//dependency/test/transitive/ext/direct,//dependency/test/transitive/ext/one,//dependency/test/transitive/ext/testonly,//dependency/test/transitive/ext/two" \
    "${REACHABILITY_ATTRIBUTION_JSON}"

check "transitive attribution roots are unioned per package" \
    "${SKYLIB} | .attributed_packages[] | select(.package == \"//dependency/test/transitive/ext/one\") | .roots | join(\",\")" \
    "//dependency/test:attribution_root" \
    "${REACHABILITY_ATTRIBUTION_JSON}"

check "multiple levels of intermediate targets still attribute the originating package" \
    "${SKYLIB} | [.attributed_packages[] | select(.package == \"//dependency/test/transitive/ext/deep\") | .production] | join(\",\")" \
    "true" \
    "${REACHABILITY_ATTRIBUTION_JSON}"

check "testonly-only attribution remains distinguishable from production attribution" \
    "${SKYLIB} | [.attributed_packages[] | select(.package == \"//dependency/test/transitive/ext/direct\" or .package == \"//dependency/test/transitive/ext/testonly\") | \"\(.package) \(.production)\"] | sort | join(\",\")" \
    "//dependency/test/transitive/ext/direct true,//dependency/test/transitive/ext/testonly false" \
    "${REACHABILITY_ATTRIBUTION_JSON}"

check "attribution unions matching packages across multiconfig analysis" \
    "${SKYLIB} | [.attributed_packages[].package] | sort | join(\",\")" \
    "//dependency/test/transitive/ext/config_default,//dependency/test/transitive/ext/config_extra" \
    "${REACHABILITY_ATTRIBUTION_MULTICONFIG_JSON}"

check "attribution multiconfig still records merged config names" \
    "${SKYLIB} | .configs | sort | join(\",\")" \
    "default,extra" \
    "${REACHABILITY_ATTRIBUTION_MULTICONFIG_JSON}"

if [ "${FAILED}" -ne 0 ]; then
    exit 1
fi

echo "All tests passed"
