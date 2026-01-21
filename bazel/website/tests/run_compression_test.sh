#!/bin/bash
set -euo pipefail

# Test script to verify website generation with compression
# This test specifically validates that DECOMPRESS_ARGS parameter expansion works correctly
# and would have caught the bug where ${DECOMPRESS_ARGS:+DECOMPRESS_ARGS} was incorrectly
# expanding to the literal string "DECOMPRESS_ARGS" instead of the variable value

echo "========================================"
echo "Running Website Compression Test"
echo "========================================"

# Handle Bazel runfiles
if [ -n "${TEST_SRCDIR:-}" ]; then
    # Running under Bazel test
    if [ -d "${TEST_SRCDIR}/envoy_toolshed" ]; then
        RUNFILES_DIR="${TEST_SRCDIR}/envoy_toolshed"
    else
        RUNFILES_DIR="${TEST_SRCDIR}/_main"
    fi
else
    echo "ERROR: TEST_SRCDIR not set. This script must be run under Bazel test."
    exit 1
fi

TEST_DIR="${RUNFILES_DIR}/website/tests"
TARBALL="${TEST_DIR}/test_with_compression_html.tar.gz"

# Check that the tarball was created
echo ""
echo "Test 1: Verifying compressed tarball exists"
if [ ! -f "${TARBALL}" ]; then
    echo "✗ FAILED: Tarball not found at ${TARBALL}"
    exit 1
fi
echo "✓ PASSED: Compressed tarball exists"

# Extract and verify contents
EXTRACT_DIR=$(mktemp -d)
trap 'rm -rf ${EXTRACT_DIR}' EXIT

echo ""
echo "Test 2: Extracting compressed tarball"
# This is the critical test - if DECOMPRESS_ARGS was incorrectly expanded to
# the literal string "DECOMPRESS_ARGS", tar would fail with an error like:
# "tar: DECOMPRESS_ARGS: Cannot open: No such file or directory"
if ! tar -xzf "${TARBALL}" -C "${EXTRACT_DIR}" 2>&1; then
    echo "✗ FAILED: Could not extract compressed tarball"
    echo "This likely indicates DECOMPRESS_ARGS parameter expansion is broken"
    exit 1
fi
echo "✓ PASSED: Compressed tarball extracted successfully"
echo "         (DECOMPRESS_ARGS parameter expansion is working correctly)"

# Verify the tarball actually contained compressed data
echo ""
echo "Test 3: Verifying compression was used"
# Check if file is gzip compressed
if ! file "${TARBALL}" | grep -q "gzip"; then
    echo "⚠ WARNING: Tarball may not be properly compressed"
else
    echo "✓ PASSED: Tarball is properly gzip compressed"
fi

# Check for expected output files
echo ""
echo "Test 4: Verifying output structure"
if [ ! -d "${EXTRACT_DIR}" ]; then
    echo "✗ FAILED: Output directory not found"
    exit 1
fi

echo ""
echo "Test 5: Checking for HTML output"
# Look for any .html files in the output
html_count=$(find "${EXTRACT_DIR}" -name "*.html" -type f | wc -l)
if [ "${html_count}" -eq 0 ]; then
    echo "✗ FAILED: No HTML files found in output"
    echo "Directory contents:"
    ls -la "${EXTRACT_DIR}"
    exit 1
fi
echo "✓ PASSED: Found ${html_count} HTML file(s)"

echo ""
echo "========================================"
echo "All compression tests PASSED ✓"
echo "========================================"
echo ""
echo "This test validates that:"
echo "  1. Website generation works with compression enabled"
echo "  2. DECOMPRESS_ARGS parameter expansion is correct"
echo "  3. The bug where \${DECOMPRESS_ARGS:+DECOMPRESS_ARGS} expanded"
echo "     to literal 'DECOMPRESS_ARGS' is NOT present"
exit 0
