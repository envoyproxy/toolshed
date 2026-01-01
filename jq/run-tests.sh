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

# Function to run a single test
run_test() {
    local test_file="$1"
    
    # Parse YAML fields using yq
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
    
    # Build the jq filter
    local jq_filter=""
    
    # Handle imports
    if [[ "$imports" != "[]" && "$imports" != "null" ]]; then
        # Parse imports array and build import statements
        local import_count
        import_count=$(echo "$imports" | jq 'length')
        for ((i=0; i<import_count; i++)); do
            local imp
            imp=$(echo "$imports" | jq -r ".[$i]")
            jq_filter+="import \"$imp\" as $imp; "
        done
    fi
    
    # Add the before filter
    jq_filter+="$before | "
    
    # Build the main expression
    if [[ -n "$module" ]]; then
        # Extract module name and function from module::function format
        local mod_name="${module%%::*}"
        local func_name="${module#*::}"
        
        # If no imports specified but module field is used, auto-import
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
    
    # Run the jq filter
    local result
    if result=$(echo "$input" | jq -L "$SCRIPT_DIR" -r "$jq_filter" 2>&1); then
        # Get the expected value as a raw string (decode from JSON)
        local expected_raw
        expected_raw=$(echo "$expected" | jq -r '.')
        
        # Compare raw strings (result has trailing newline, so remove it)
        local result_trimmed="${result%$'\n'}"
        
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

# Main execution
main() {
    local test_dir="$SCRIPT_DIR/tests"
    
    if [[ ! -d "$test_dir" ]]; then
        echo "Error: Test directory not found: $test_dir"
        exit 1
    fi
    
    # Find all test files
    local test_files=()
    while IFS= read -r -d '' file; do
        test_files+=("$file")
    done < <(find "$test_dir" -type f \( -name "*.test.yaml" -o -name "*.test.yml" \) -print0 | sort -z)
    
    if [[ ${#test_files[@]} -eq 0 ]]; then
        echo "No test files found in $test_dir"
        exit 1
    fi
    
    echo "Running ${#test_files[@]} test(s)..."
    echo ""
    
    # Run each test
    for test_file in "${test_files[@]}"; do
        run_test "$test_file" || true
    done
    
    # Print summary
    echo ""
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
    
    # Exit with failure if any tests failed
    if [[ $FAILED -gt 0 ]]; then
        exit 1
    fi
}

# Run main function
main "$@"
