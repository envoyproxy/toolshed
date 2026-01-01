#!/usr/bin/env bash

# Test runner for jq modules
# Finds and runs all *.test.yaml and *.test.yml files in jq/tests/

set -euo pipefail

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

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
        yq eval ".$field // \"$default\"" "$test_file"
    else
        yq eval ".$field // \"\"" "$test_file"
    fi
}

build_imports () {
    local imports="$1"
    local jq_filter=""

    if [[ "$imports" != "[]" && "$imports" != "null" ]]; then
        local import_count
        import_count=$(echo "$imports" | jq 'length')
        for ((i=0; i<import_count; i++)); do
            local imp
            imp=$(echo "$imports" | jq -r ".[$i]")
            jq_filter+="import \"$imp\" as $imp; "
        done
    fi
    echo "$jq_filter"
}

build_jq_filter () {
    local test_file="$1"
    local jq_filter=""

    local imports
    imports=$(yq eval '.imports // []' "$test_file" -o json)
    local before
    before=$(parse_test_field "$test_file" "before" ".")
    local module
    module=$(parse_test_field "$test_file" "module")
    local expression
    expression=$(parse_test_field "$test_file" "expression")

    jq_filter+=$(build_imports "$imports")
    jq_filter+="$before | "

    if [[ -n "$module" && "$module" != "" ]]; then
        local mod_name="${module%%::*}"
        local func_name="${module#*::}"
        if [[ "$imports" == "[]" || "$imports" == "null" ]]; then
            jq_filter="import \"$mod_name\" as $mod_name; $jq_filter"
        fi
        jq_filter+="$mod_name::$func_name"
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
    local input
    input=$(yq eval '.input' "$test_file" -o json)
    local expected
    expected=$(yq eval '.expected' "$test_file" -o json)

    local jq_filter
    if ! jq_filter=$(build_jq_filter "$test_file"); then
        echo -e "${RED}✗${NC} $name"
        echo "  Error: Test must specify either 'module' or 'expression' field"
        test_failed "$name" "" ""
        return 1
    fi

    local result
    if result=$(echo "$input" | jq -L "$SCRIPT_DIR" -r "$jq_filter" 2>&1); then
        local result_trimmed="${result%$'\n'}"
        local expected_raw
        expected_raw=$(echo "$expected" | jq -r '.')

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
    local test_dir="$SCRIPT_DIR/tests"
    local test_files=()

    if [[ ! -d "$test_dir" ]]; then
        echo "Error: Test directory not found: $test_dir"
        exit 1
    fi
    while IFS= read -r -d '' file; do
        test_files+=("$file")
    done < <(find "$test_dir" -type f \( -name "*.test.yaml" -o -name "*.test.yml" \) -print0 | sort -z)
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
    run_tests
    summary
    if [[ $FAILED -gt 0 ]]; then
        exit 1
    fi
}

main "$@"
