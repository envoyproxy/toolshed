#!/bin/bash

set -euo pipefail

if [ -n "${TEST_SRCDIR:-}" ]; then
    if [ -d "${TEST_SRCDIR}/envoy_toolshed" ]; then
        RUNFILES_DIR="${TEST_SRCDIR}/envoy_toolshed"
    else
        RUNFILES_DIR="${TEST_SRCDIR}/_main"
    fi
else
    echo "This test must be run under Bazel" >&2
    exit 1
fi

JQ="${JQ_BIN:-jq}"
REACHABILITY_EXCLUDED_EDGE_JSON="${RUNFILES_DIR}/dependency/test/reachability_excluded_edge.json"
REACHABILITY_EDGE_AND_PATTERN_JSON="${RUNFILES_DIR}/dependency/test/reachability_edge_and_pattern.json"
REACHABILITY_EXCLUDED_PATTERN_JSON="${RUNFILES_DIR}/dependency/test/reachability_excluded_pattern.json"
REACHABILITY_APPARENT_EXCLUSION_BASELINE_JSON="${RUNFILES_DIR}/dependency/test/reachability_apparent_exclusion_baseline.json"
REACHABILITY_APPARENT_EXCLUSION_JSON="${RUNFILES_DIR}/dependency/test/reachability_apparent_exclusion.json"
REACHABILITY_RULES_PKG_TRANSITIVE_JSON="${RUNFILES_DIR}/dependency/test/reachability_rules_pkg_transitive.json"
REACHABILITY_EXCLUDED_RULES_PKG_TRANSITIVE_JSON="${RUNFILES_DIR}/dependency/test/reachability_excluded_rules_pkg_transitive.json"
REACHABILITY_EMPTY_EXCLUSIONS_JSON="${RUNFILES_DIR}/dependency/test/reachability_empty_exclusions.json"
REACHABILITY_EMPTY_EXCLUSIONS_EXPLICIT_JSON="${RUNFILES_DIR}/dependency/test/reachability_empty_exclusions_explicit.json"
REACHABILITY_ATTRIBUTION_EXCLUDED_BASELINE_JSON="${RUNFILES_DIR}/dependency/test/reachability_attribution_excluded_baseline.json"
REACHABILITY_ATTRIBUTION_EXCLUDED_JSON="${RUNFILES_DIR}/dependency/test/reachability_attribution_excluded.json"

FAILED=0

check() {
    local description="$1"
    local query="$2"
    local expected="$3"
    local file="$4"
    local actual
    actual="$("${JQ}" -r "${query}" "${file}")"
    if [ "${actual}" != "${expected}" ]; then
        echo "FAIL: ${description}" >&2
        echo "  file:     ${file}" >&2
        echo "  query:    ${query}" >&2
        echo "  expected: ${expected}" >&2
        echo "  actual:   ${actual}" >&2
        FAILED=1
    else
        echo "PASS: ${description}"
    fi
}

check "excluded_edges removes only the excluded attribute edge" \
    '.dependencies | to_entries[] | select(.value.name == "bazel_skylib") | .value.targets | map(sub("^@+[^/]*//"; "//")) | sort | join(",")' \
    "//lib:sets" \
    "${REACHABILITY_EXCLUDED_EDGE_JSON}"

check "excluded_edges still keeps independent path to same repository" \
    '.dependencies | to_entries[] | select(.value.name == "bazel_skylib") | .value.consumers | map(select(.repo == "") | .target) | sort | join(",")' \
    "//dependency/test:excluded_edge_root" \
    "${REACHABILITY_EXCLUDED_EDGE_JSON}"

check "excluded_edges prunes transitively behind the excluded attribute" \
    '[.dependencies[] | .name] | any(. == "rules_shell")' \
    "false" \
    "${REACHABILITY_EXCLUDED_EDGE_JSON}"

check "excluded_patterns can exclude multiple repos from one prefix" \
    '[.dependencies[] | .name] | any(. == "bazel_skylib" or . == "bazel_tools")' \
    "false" \
    "${REACHABILITY_EXCLUDED_PATTERN_JSON}"

check "excluded_patterns can remove all matching deps from one root" \
    '[.dependencies[] | .name] | length' \
    "0" \
    "${REACHABILITY_EXCLUDED_PATTERN_JSON}"

check "excluded_patterns baseline includes the matched boundary repo" \
    '[.dependencies[] | .name] | any(. == "rules_pkg")' \
    "true" \
    "${REACHABILITY_RULES_PKG_TRANSITIVE_JSON}"

check "excluded_patterns prunes matched repos transitively" \
    '[.dependencies[] | .name] | length' \
    "0" \
    "${REACHABILITY_EXCLUDED_RULES_PKG_TRANSITIVE_JSON}"

check "combined excluded_edges and excluded_patterns apply together" \
    '[.dependencies[] | .name] | length' \
    "0" \
    "${REACHABILITY_EDGE_AND_PATTERN_JSON}"

check "baseline records extension repo by apparent name" \
    '[.dependencies | to_entries[] | select(.value.name == "apparent_excluded_repo")] | length' \
    "1" \
    "${REACHABILITY_APPARENT_EXCLUSION_BASELINE_JSON}"

check "baseline reaches through bzlmod extension repo before apparent-name exclusion" \
    '[.dependencies[] | .name] | any(. == "apparent_excluded_transitive_repo")' \
    "true" \
    "${REACHABILITY_APPARENT_EXCLUSION_BASELINE_JSON}"

check "apparent-name excluded bzlmod extension repo is not recorded" \
    '[.dependencies[] | .name] | any(. == "apparent_excluded_repo")' \
    "false" \
    "${REACHABILITY_APPARENT_EXCLUSION_JSON}"

check "apparent-name excluded bzlmod extension repo is pruned transitively" \
    '[.dependencies[] | .name] | any(. == "apparent_excluded_transitive_repo")' \
    "false" \
    "${REACHABILITY_APPARENT_EXCLUSION_JSON}"

check "baseline attribution records the unexcluded repository" \
    '.dependencies | to_entries[] | select(.value.name == "rules_pkg") | .value.attributed_packages[0].package' \
    "//dependency/test/transitive/ext/excluded" \
    "${REACHABILITY_ATTRIBUTION_EXCLUDED_BASELINE_JSON}"

check "excluded repository is not attributed" \
    '[.dependencies[] | select(.name == "rules_pkg")] | length' \
    "0" \
    "${REACHABILITY_ATTRIBUTION_EXCLUDED_JSON}"

check "nothing is attributed through an excluded repository" \
    '[.dependencies[] | .attributed_packages[]?] | length' \
    "0" \
    "${REACHABILITY_ATTRIBUTION_EXCLUDED_JSON}"

if ! cmp -s "${REACHABILITY_EMPTY_EXCLUSIONS_JSON}" "${REACHABILITY_EMPTY_EXCLUSIONS_EXPLICIT_JSON}"; then
    echo "FAIL: explicit empty exclusions must be byte-identical to defaults" >&2
    FAILED=1
else
    echo "PASS: explicit empty exclusions must be byte-identical to defaults"
fi

if [ "${FAILED}" -ne 0 ]; then
    exit 1
fi

echo "All tests passed"
