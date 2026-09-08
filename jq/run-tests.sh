#!/usr/bin/env bash

# Test runner for jq modules
# Finds and runs all *.test.yaml and *.test.yml files in jq/tests/, or in a
# single test subdirectory when one is given as an argument, eg:
#
#   ./jq/run-tests.sh
#   ./jq/run-tests.sh tests/github/gfm

set -euo pipefail

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Resolve rlocation-style JQ_BIN/YQ_BIN (as set eg by Bazel's aspect jq/yq
# toolchains) to real binary paths. Left untouched (and defaulted to the
# binary on PATH) for bare/non-Bazel invocation.
_resolve_runfiles_bin () {
    local var_name="$1"
    local value="${!var_name:-}"

    if [[ -n "$value" && "$value" != /* ]]; then
        local f=bazel_tools/tools/bash/runfiles/runfiles.bash
        local runfiles_dir="${RUNFILES_DIR:-}"
        if [[ -z "$runfiles_dir" && -n "${TEST_SRCDIR:-}" ]]; then
            runfiles_dir="${TEST_SRCDIR}"
        fi
        local runfiles_bash_path="${runfiles_dir:-/dev/null}/$f"
        # shellcheck disable=SC1090
        source "$runfiles_bash_path" 2>/dev/null || \
            source "$(grep -sm1 "^$f " "${RUNFILES_MANIFEST_FILE:-/dev/null}" | cut -f2 -d' ')" 2>/dev/null || \
            { echo >&2 "ERROR: cannot find runfiles.bash"; exit 1; }
        value="$(rlocation "$value")"
    fi
    echo "$value"
}

JQ="$(_resolve_runfiles_bin JQ_BIN)"
JQ="${JQ:-jq}"
YQ="$(_resolve_runfiles_bin YQ_BIN)"
YQ="${YQ:-yq}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

# Counters
PASSED=0
FAILED=0
FAILED_TESTS=()

parse_test_field () {
    local test_file="$1"
    local field="$2"
    local default="${3:-}"

    if [[ -n "$default" ]]; then
        "$YQ" eval ".$field // \"$default\"" "$test_file"
    else
        "$YQ" eval ".$field // \"\"" "$test_file"
    fi
}

build_imports () {
    local imports="$1"
    local jq_filter=""

    if [[ "$imports" != "[]" && "$imports" != "null" ]]; then
        local import_count
        import_count=$(echo "$imports" | "$JQ" 'length')
        for ((i=0; i<import_count; i++)); do
            local imp
            imp=$(echo "$imports" | "$JQ" -r ".[$i]")
            # The import alias is always the last path segment, eg
            # `import "github/gfm" as gfm;`, so scoped modules can be
            # referred to by their short name in expressions.
            local mod_alias="${imp##*/}"
            jq_filter+="import \"$imp\" as $mod_alias; "
        done
    fi
    echo "$jq_filter"
}

build_jq_filter () {
    local test_file="$1"
    local jq_filter=""

    local imports
    imports=$("$YQ" eval '.imports // []' "$test_file" -o json)
    local before
    before=$(parse_test_field "$test_file" "before" ".")
    local module
    module=$(parse_test_field "$test_file" "module")
    local expression
    expression=$(parse_test_field "$test_file" "expression")

    jq_filter+=$(build_imports "$imports")
    jq_filter+="$before | "

    if [[ -n "$module" && "$module" != "" ]]; then
        local mod_path="${module%%::*}"
        local func_name="${module#*::}"
        local mod_alias="${mod_path##*/}"
        if [[ "$imports" == "[]" || "$imports" == "null" ]]; then
            jq_filter="import \"$mod_path\" as $mod_alias; $jq_filter"
        fi
        jq_filter+="$mod_alias::$func_name"
    elif [[ -n "$expression" && "$expression" != "" ]]; then
        jq_filter+="$expression"
    else
        return 1
    fi
    echo "$jq_filter"
}

test_passed () {
    local name="$1"
    echo -e "${GREEN}✓${NC} $name"
    ((PASSED++))
}

test_failed () {
    local name="$1"
    local expected="$2"
    local got="$3"
    echo -e "${RED}✗${NC} $name"
    if [[ -n "$expected" ]]; then
        echo "  expected: $expected"
        echo "  got:      $got"
    fi
    ((FAILED++))
    FAILED_TESTS+=("$name")
}

run_test () {
    local test_file="$1"

    local name
    name=$(parse_test_field "$test_file" "name")
    local raw
    raw=$(parse_test_field "$test_file" "raw" "false")

    local jq_filter
    if ! jq_filter=$(build_jq_filter "$test_file"); then
        echo -e "${RED}✗${NC} $name"
        echo "  Error: Test must specify either 'module' or 'expression' field"
        test_failed "$name" "" ""
        return 1
    fi

    local result

    if [[ "$raw" == "true" ]]; then
        # Raw mode feeds `.input` to jq as text (`-R`), one line per jq
        # `input`/`.`, for filters that parse raw (non-JSON) text - eg
        # `clang/tidy`.
        local input_raw
        input_raw=$("$YQ" eval '.input' "$test_file")
        if ! result=$(printf '%s' "$input_raw" | "$JQ" -R -L "$SCRIPT_DIR" "$jq_filter" 2>&1); then
            echo -e "${RED}✗${NC} $name"
            echo "  Error running jq filter:"
            echo "  $result"
            test_failed "$name" "" ""
            return 1
        fi
        local expected_json
        expected_json=$("$YQ" eval '.expected' "$test_file" -o json)
        local result_norm
        result_norm=$(echo "$result" | "$JQ" -S .)
        local expected_norm
        expected_norm=$(echo "$expected_json" | "$JQ" -S .)
        if [[ "$result_norm" == "$expected_norm" ]]; then
            test_passed "$name"
            return 0
        else
            test_failed "$name" "$expected_norm" "$result_norm"
            return 1
        fi
    fi

    local input
    input=$("$YQ" eval '.input' "$test_file" -o json)
    local expected
    expected=$("$YQ" eval '.expected' "$test_file" -o json)

    if result=$(echo "$input" | "$JQ" -L "$SCRIPT_DIR" -r "$jq_filter" 2>&1); then
        local result_trimmed="${result%$'\n'}"
        local expected_raw
        expected_raw=$(echo "$expected" | "$JQ" -r '.')

        if [[ "$result_trimmed" == "$expected_raw" ]]; then
            test_passed "$name"
            return 0
        else
            test_failed "$name" "$expected_raw" "$result_trimmed"
            return 1
        fi
    else
        echo -e "${RED}✗${NC} $name"
        echo "  Error running jq filter:"
        echo "  $result"
        test_failed "$name" "" ""
        return 1
    fi
}

summary () {
    echo "================================"
    if [[ $FAILED -eq 0 ]]; then
        echo -e "${GREEN}All tests passed!${NC}"
        echo "$PASSED passed"
    else
        echo -e "${RED}Some tests failed!${NC}"
        echo "$PASSED passed, $FAILED failed"
        echo ""
        echo "Failed tests:"
        for test_name in "${FAILED_TESTS[@]}"; do
            echo "  - $test_name"
        done
    fi
    echo "================================"
}

run_tests () {
    local test_subdir="${1:-tests}"
    local test_dir="$test_subdir"
    if [[ "$test_dir" != /* ]]; then
        test_dir="$SCRIPT_DIR/$test_subdir"
    fi
    local test_files=()

    if [[ ! -d "$test_dir" ]]; then
        echo "Error: Test directory not found: $test_dir"
        exit 1
    fi
    while IFS= read -r -d '' file; do
        test_files+=("$file")
    done < <(find -L "$test_dir" -type f \( -name "*.test.yaml" -o -name "*.test.yml" \) -print0 | sort -z)
    if [[ ${#test_files[@]} -eq 0 ]]; then
        echo "No test files found in $test_dir"
        exit 1
    fi
    echo "Running ${#test_files[@]} test(s)..."
    echo ""
    for test_file in "${test_files[@]}"; do
        run_test "$test_file" || :
    done
    echo ""
}

main() {
    run_tests "$@"
    summary
    if [[ $FAILED -gt 0 ]]; then
        exit 1
    fi
}

main "$@"
