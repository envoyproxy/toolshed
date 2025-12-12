#!/bin/bash
# Test script for clang-tidy parser

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PARSER="${SCRIPT_DIR}/../parse_clang_tidy.jq"

echo "Testing clang-tidy parser..."

# Check if jq is available
if ! command -v jq &> /dev/null; then
    echo "ERROR: jq is not installed"
    exit 1
fi

# Function to run a single test
run_test() {
    local input_file="$1"
    local expected_file="$2"
    local test_name="$3"
    
    echo ""
    echo "Running test: ${test_name}"
    
    local actual_output
    actual_output=$(mktemp)
    
    # Run the parser
    if ! jq -Rf "${PARSER}" < "${input_file}" > "${actual_output}" 2>&1; then
        echo "✗ Test FAILED: Parser error"
        cat "${actual_output}"
        rm -f "${actual_output}"
        return 1
    fi
    
    # Compare outputs
    if diff -q "${expected_file}" "${actual_output}" > /dev/null 2>&1; then
        echo "✓ Test PASSED: ${test_name}"
        rm -f "${actual_output}"
        return 0
    else
        echo "✗ Test FAILED: ${test_name}"
        echo ""
        echo "Diff:"
        diff -u "${expected_file}" "${actual_output}" || true
        echo ""
        echo "Actual output:"
        cat "${actual_output}"
        rm -f "${actual_output}"
        return 1
    fi
}

# Run all tests
failed=0

# Test 1: Sample input with multiple diagnostics
if ! run_test \
    "${SCRIPT_DIR}/sample_input.txt" \
    "${SCRIPT_DIR}/expected_output.json" \
    "Sample input (multiple diagnostics)"; then
    failed=$((failed + 1))
fi

# Test 2: Simple error
if ! run_test \
    "${SCRIPT_DIR}/simple_error.txt" \
    "${SCRIPT_DIR}/simple_error_expected.json" \
    "Simple error"; then
    failed=$((failed + 1))
fi

# Test 3: No diagnostics
if ! run_test \
    "${SCRIPT_DIR}/no_diagnostics.txt" \
    "${SCRIPT_DIR}/no_diagnostics_expected.json" \
    "No diagnostics"; then
    failed=$((failed + 1))
fi

# Summary
echo ""
echo "================================"
if [ $failed -eq 0 ]; then
    echo "All tests PASSED ✓"
    exit 0
else
    echo "${failed} test(s) FAILED ✗"
    exit 1
fi
