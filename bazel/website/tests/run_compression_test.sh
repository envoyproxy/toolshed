#!/bin/bash

# --- begin runfiles.bash initialization v3 ---
set -uo pipefail; set +e; f=bazel_tools/tools/bash/runfiles/runfiles.bash
source "${RUNFILES_DIR:-/dev/null}/$f" 2>/dev/null || \
  source "$(grep -sm1 "^$f " "${RUNFILES_MANIFEST_FILE:-/dev/null}" | cut -f2- -d' ')" 2>/dev/null || \
  source "$0.runfiles/$f" 2>/dev/null || \
  source "$(grep -sm1 "^$f " "$0.runfiles_manifest" | cut -f2- -d' ')" 2>/dev/null || \
  source "$(grep -sm1 "^$f " "$0.exe.runfiles_manifest" | cut -f2- -d' ')" 2>/dev/null || \
  { echo>&2 "ERROR: cannot find $f"; exit 1; }; f=; set -e
# --- end runfiles.bash initialization v3 ---

# Test script to verify website generation with compression

echo "========================================"
echo "Running Website Compression Test"
echo "========================================"

TARBALL="$(rlocation "$1")"

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
    exit 1
fi
echo "✓ PASSED: Compressed tarball extracted successfully"

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
exit 0
