#!/bin/bash
set -euo pipefail

# Test script for provider architecture
# Verifies WebsiteAssetInfo and WebsiteGeneratorInfo providers work correctly

echo "======================================="
echo "Running Provider Architecture Tests"
echo "======================================="

# Handle Bazel runfiles
if [ -n "${TEST_SRCDIR:-}" ]; then
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
failed=0

# Test 1: Mock generator with markdown assets
echo ""
echo "Test 1: Mock generator with markdown assets"
TARBALL="${TEST_DIR}/test_mock_markdown_html.tar.gz"
if [ ! -f "${TARBALL}" ]; then
    echo "✗ FAILED: Mock markdown tarball not found"
    failed=$((failed + 1))
else
    EXTRACT_DIR=$(mktemp -d)
    trap 'rm -rf ${EXTRACT_DIR}' EXIT
    
    if tar -xzf "${TARBALL}" -C "${EXTRACT_DIR}" 2>&1; then
        echo "✓ PASSED: Mock markdown tarball extracted"
        
        # Verify index.html was created
        if [ -f "${EXTRACT_DIR}/index.html" ]; then
            echo "✓ PASSED: Mock generator created index.html"
            
            # Check it contains expected content
            if grep -q "Mock Generated Site" "${EXTRACT_DIR}/index.html"; then
                echo "✓ PASSED: Output contains mock generator content"
            else
                echo "✗ FAILED: Output missing mock generator content"
                failed=$((failed + 1))
            fi
        else
            echo "✗ FAILED: Mock generator did not create index.html"
            failed=$((failed + 1))
        fi
    else
        echo "✗ FAILED: Could not extract mock markdown tarball"
        failed=$((failed + 1))
    fi
fi

# Test 2: Sphinx generator skeleton
echo ""
echo "Test 2: Sphinx generator skeleton"
TARBALL="${TEST_DIR}/test_sphinx_skeleton_html.tar.gz"
if [ ! -f "${TARBALL}" ]; then
    echo "✗ FAILED: Sphinx skeleton tarball not found"
    failed=$((failed + 1))
else
    EXTRACT_DIR=$(mktemp -d)
    
    if tar -xzf "${TARBALL}" -C "${EXTRACT_DIR}" 2>&1; then
        echo "✓ PASSED: Sphinx skeleton tarball extracted"
        
        # Verify index.html was created
        if [ -f "${EXTRACT_DIR}/index.html" ]; then
            echo "✓ PASSED: Sphinx skeleton created index.html"
            
            # Check it contains expected content
            if grep -q "Sphinx Generator Skeleton" "${EXTRACT_DIR}/index.html"; then
                echo "✓ PASSED: Output contains Sphinx skeleton content"
            else
                echo "✗ FAILED: Output missing Sphinx skeleton content"
                failed=$((failed + 1))
            fi
        else
            echo "✗ FAILED: Sphinx skeleton did not create index.html"
            failed=$((failed + 1))
        fi
    else
        echo "✗ FAILED: Could not extract Sphinx skeleton tarball"
        failed=$((failed + 1))
    fi
fi

# Test 3: Yew generator skeleton
echo ""
echo "Test 3: Yew generator skeleton"
TARBALL="${TEST_DIR}/test_yew_skeleton_html.tar.gz"
if [ ! -f "${TARBALL}" ]; then
    echo "✗ FAILED: Yew skeleton tarball not found"
    failed=$((failed + 1))
else
    EXTRACT_DIR=$(mktemp -d)
    
    if tar -xzf "${TARBALL}" -C "${EXTRACT_DIR}" 2>&1; then
        echo "✓ PASSED: Yew skeleton tarball extracted"
        
        # Verify index.html was created
        if [ -f "${EXTRACT_DIR}/index.html" ]; then
            echo "✓ PASSED: Yew skeleton created index.html"
            
            # Check it contains expected content
            if grep -q "Yew/WASM Generator Skeleton" "${EXTRACT_DIR}/index.html"; then
                echo "✓ PASSED: Output contains Yew skeleton content"
            else
                echo "✗ FAILED: Output missing Yew skeleton content"
                failed=$((failed + 1))
            fi
        else
            echo "✗ FAILED: Yew skeleton did not create index.html"
            failed=$((failed + 1))
        fi
    else
        echo "✗ FAILED: Could not extract Yew skeleton tarball"
        failed=$((failed + 1))
    fi
fi

# Test 4: Mixed asset types with mock generator
echo ""
echo "Test 4: Mixed asset types with mock generator"
TARBALL="${TEST_DIR}/test_mock_mixed_html.tar.gz"
if [ ! -f "${TARBALL}" ]; then
    echo "✗ FAILED: Mock mixed assets tarball not found"
    failed=$((failed + 1))
else
    EXTRACT_DIR=$(mktemp -d)
    
    if tar -xzf "${TARBALL}" -C "${EXTRACT_DIR}" 2>&1; then
        echo "✓ PASSED: Mock mixed assets tarball extracted"
        
        # Verify output
        if [ -f "${EXTRACT_DIR}/index.html" ]; then
            echo "✓ PASSED: Mock generator handled mixed assets"
        else
            echo "✗ FAILED: Mock generator failed with mixed assets"
            failed=$((failed + 1))
        fi
    else
        echo "✗ FAILED: Could not extract mock mixed assets tarball"
        failed=$((failed + 1))
    fi
fi

echo ""
echo "======================================="
if [ $failed -eq 0 ]; then
    echo "All provider architecture tests PASSED ✓"
    exit 0
else
    echo "${failed} provider architecture test(s) FAILED ✗"
    exit 1
fi
