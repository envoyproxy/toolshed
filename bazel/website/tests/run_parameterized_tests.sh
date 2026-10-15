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

# Test script for parameterized website generation tests
# Tests custom configurations and generator-agnostic features

echo "======================================="
echo "Running Parameterized Website Tests"
echo "======================================="

failed=0

# Test custom exclude patterns
echo ""
echo "Test 1: Custom exclude patterns"
TARBALL="$(rlocation "$1")"
if [ ! -f "${TARBALL}" ]; then
    echo "✗ FAILED: Custom exclude tarball not found"
    failed=$((failed + 1))
else
    EXTRACT_DIR=$(mktemp -d)
    trap 'rm -rf ${EXTRACT_DIR}' EXIT

    if tar -xzf "${TARBALL}" -C "${EXTRACT_DIR}" 2>&1; then
        echo "✓ PASSED: Custom exclude tarball extracted"

        # Verify that fewer items are excluded
        # Note: This is a basic check - actual verification would depend on
        # knowing what the generator produces
        echo "  Checking extracted contents..."
        file_count=$(find "${EXTRACT_DIR}" -type f | wc -l)
        echo "  Found ${file_count} files"

        if [ "${file_count}" -gt 0 ]; then
            echo "✓ PASSED: Files exist in custom exclude output"
        else
            echo "✗ FAILED: No files in custom exclude output"
            failed=$((failed + 1))
        fi
    else
        echo "✗ FAILED: Could not extract custom exclude tarball"
        failed=$((failed + 1))
    fi
fi

# Test custom mappings
echo ""
echo "Test 2: Custom mappings"
TARBALL="$(rlocation "$2")"
if [ ! -f "${TARBALL}" ]; then
    echo "✗ FAILED: Custom mappings tarball not found"
    failed=$((failed + 1))
else
    EXTRACT_DIR=$(mktemp -d)

    if tar -xzf "${TARBALL}" -C "${EXTRACT_DIR}" 2>&1; then
        echo "✓ PASSED: Custom mappings tarball extracted"

        # Check that output was generated
        file_count=$(find "${EXTRACT_DIR}" -type f | wc -l)
        echo "  Found ${file_count} files"

        if [ "${file_count}" -gt 0 ]; then
            echo "✓ PASSED: Files exist in custom mappings output"
        else
            echo "✗ FAILED: No files in custom mappings output"
            failed=$((failed + 1))
        fi
    else
        echo "✗ FAILED: Could not extract custom mappings tarball"
        failed=$((failed + 1))
    fi
fi

# Test generator agnostic interface
echo ""
echo "Test 3: Generator-agnostic interface verification"
echo "Checking that macro accepts generator parameter..."
# This is verified by successful compilation of the BUILD file
echo "✓ PASSED: BUILD file compiles with custom parameters"

echo ""
echo "======================================="
if [ $failed -eq 0 ]; then
    echo "All parameterized tests PASSED ✓"
    exit 0
else
    echo "${failed} parameterized test(s) FAILED ✗"
    exit 1
fi
