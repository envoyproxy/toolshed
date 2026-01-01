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

run_test () {
    local test_file="$1"
    local jq_filter=""

    local name
    name=$(yq eval '.name' "$test_file")
    local input
    input=$(yq eval '.input' "$test_file" -o json)
    local expected
    expected=$(yq eval '.expected' "$test_file" -o json)
    local before
    before=$(yq eval '.before // "."' "$test_file")
    local module
    module=$(yq eval '.module // ""' "$test_file")
    local expression
    expression=$(yq eval '.expression // ""' "$test_file")
    local imports
    imports=$(yq eval '.imports // []' "$test_file" -o json)

    if [[ "$imports" != "[]" && "$imports" != "null" ]]; then
        local import_count
        import_count=$(echo "$imports" | jq 'length')
        for ((i=0; i<import_count; i++)); do
            local imp
            imp=$(echo "$imports" | jq -r ".[$i]")
            jq_filter+="import \"$imp\" as $imp; "
        done
    fi
    jq_filter+="$before | "
    if [[ -n "$module" ]]; then
        local mod_name="${module%%::*}"
        local func_name="${module#*::}"
        if [[ "$imports" == "[]" || "$imports" == "null" ]]; then
            jq_filter="import \"$mod_name\" as $mod_name; $jq_filter"
        fi
        jq_filter+="$mod_name::$func_name"
    elif [[ -n "$expression" ]]; then
        jq_filter+="$expression"
    else
        echo -e "${RED}✗${NC} $name"
        echo "  Error: Test must specify either 'module' or 'expression' field"
        return 1
    fi
    local result
    if result=$(echo "$input" | jq -L "$SCRIPT_DIR" -r "$jq_filter" 2>&1); then
        local result_trimmed="${result%$'\n'}"
        local expected_raw
        expected_raw=$(echo "$expected" | jq -r '.')

        if [[ "$result_trimmed" == "$expected_raw" ]]; then
            echo -e "${GREEN}✓${NC} $name"
            ((PASSED++))
            return 0
        else
            echo -e "${RED}✗${NC} $name"
            echo "  expected: $expected_raw"
            echo "  got:      $result_trimmed"
            ((FAILED++))
            FAILED_TESTS+=("$name")
            return 1
        fi
    else
        echo -e "${RED}✗${NC} $name"
        echo "  Error running jq filter:"
        echo "  $result"
        ((FAILED++))
        FAILED_TESTS+=("$name")
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
