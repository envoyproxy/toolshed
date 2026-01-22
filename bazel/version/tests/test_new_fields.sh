#!/bin/bash
# Test that module_versions outputs the required new fields for Envoy compatibility
# Tests for: version, urls, minimum_version fields

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Ensure JQ is available
if [ -z "${JQ_BIN:-}" ]; then
    if ! command -v jq &> /dev/null; then
        echo "ERROR: jq is not available. JQ_BIN environment variable is not set and 'jq' is not in PATH." >&2
        exit 1
    fi
    JQ="jq"
else
    JQ="${JQ_BIN}"
fi

OUTPUT_FILE="${SCRIPT_DIR}/test_versions.json"

if [ ! -f "$OUTPUT_FILE" ]; then
    echo "ERROR: Output file $OUTPUT_FILE does not exist" >&2
    exit 1
fi

failures=0

echo "Testing module_versions output structure..."
echo ""

# Test 1: Check that 'version' field exists (not 'resolved_version')
echo "Test 1: Checking 'version' field exists for all modules"
has_version=$("$JQ" -r 'all(.[]; has("version"))' "$OUTPUT_FILE")
if [ "$has_version" = "true" ]; then
    echo "  ✓ PASS: All modules have 'version' field"
else
    echo "  ✗ FAIL: Some modules are missing 'version' field"
    ((failures++))
fi

# Test 2: Check that 'resolved_version' field does NOT exist (renamed to 'version')
echo "Test 2: Checking 'resolved_version' field does not exist"
has_resolved=$("$JQ" -r 'any(.[]; has("resolved_version"))' "$OUTPUT_FILE")
if [ "$has_resolved" = "false" ]; then
    echo "  ✓ PASS: No modules have 'resolved_version' field (correctly renamed to 'version')"
else
    echo "  ✗ FAIL: Some modules still have 'resolved_version' field"
    ((failures++))
fi

# Test 3: Check that 'urls' field exists and is an array
echo "Test 3: Checking 'urls' field exists and is an array for all modules"
urls_valid=$("$JQ" -r 'all(.[]; has("urls") and (.urls | type == "array"))' "$OUTPUT_FILE")
if [ "$urls_valid" = "true" ]; then
    echo "  ✓ PASS: All modules have 'urls' field as an array"
else
    echo "  ✗ FAIL: Some modules are missing 'urls' field or it's not an array"
    ((failures++))
fi

# Test 4: Check that 'urls' array is not empty
echo "Test 4: Checking 'urls' arrays are not empty"
urls_not_empty=$("$JQ" -r 'all(.[]; .urls | length > 0)' "$OUTPUT_FILE")
if [ "$urls_not_empty" = "true" ]; then
    echo "  ✓ PASS: All modules have non-empty 'urls' arrays"
else
    echo "  ✗ FAIL: Some modules have empty 'urls' arrays"
    ((failures++))
fi

# Test 5: Check that 'urls' contain expected format (registry URL with source.json)
echo "Test 5: Checking 'urls' contain source.json URLs"
urls_format=$("$JQ" -r 'all(.[] | .urls[0]; test("/modules/.+/[^/]+/source\\.json$"))' "$OUTPUT_FILE")
if [ "$urls_format" = "true" ]; then
    echo "  ✓ PASS: All 'urls' follow expected format (.../modules/NAME/VERSION/source.json)"
else
    echo "  ✗ FAIL: Some 'urls' do not follow expected format"
    echo "  Expected format: .../modules/NAME/VERSION/source.json"
    ((failures++))
fi

# Test 6: Check that 'minimum_version' field exists
echo "Test 6: Checking 'minimum_version' field exists for all modules"
has_minimum=$("$JQ" -r 'all(.[]; has("minimum_version"))' "$OUTPUT_FILE")
if [ "$has_minimum" = "true" ]; then
    echo "  ✓ PASS: All modules have 'minimum_version' field"
else
    echo "  ✗ FAIL: Some modules are missing 'minimum_version' field"
    ((failures++))
fi

# Test 7: Check that 'registry' field exists
echo "Test 7: Checking 'registry' field exists for all modules"
has_registry=$("$JQ" -r 'all(.[]; has("registry"))' "$OUTPUT_FILE")
if [ "$has_registry" = "true" ]; then
    echo "  ✓ PASS: All modules have 'registry' field"
else
    echo "  ✗ FAIL: Some modules are missing 'registry' field"
    ((failures++))
fi

# Test 8: Check URL construction matches registry + module path
echo "Test 8: Checking URL construction matches registry + module path"
url_construction_valid=$("$JQ" -r '
  all(. | to_entries[]; 
    .value.urls[0] == (.value.registry + "/modules/" + .key + "/" + .value.version + "/source.json")
  )
' "$OUTPUT_FILE")
if [ "$url_construction_valid" = "true" ]; then
    echo "  ✓ PASS: URLs correctly constructed from registry + module name + version"
else
    echo "  ✗ FAIL: Some URLs not correctly constructed"
    ((failures++))
fi

# Test 9: Verify specific example (aspect_bazel_lib)
echo "Test 9: Checking specific module (aspect_bazel_lib) has correct structure"
if "$JQ" -e '.aspect_bazel_lib' "$OUTPUT_FILE" > /dev/null 2>&1; then
    aspect_version=$("$JQ" -r '.aspect_bazel_lib.version' "$OUTPUT_FILE")
    aspect_min=$("$JQ" -r '.aspect_bazel_lib.minimum_version' "$OUTPUT_FILE")
    aspect_urls=$("$JQ" -r '.aspect_bazel_lib.urls | length' "$OUTPUT_FILE")
    aspect_registry=$("$JQ" -r '.aspect_bazel_lib.registry' "$OUTPUT_FILE")
    
    if [ -n "$aspect_version" ] && [ -n "$aspect_min" ] && [ "$aspect_urls" -gt 0 ] && [ -n "$aspect_registry" ]; then
        echo "  ✓ PASS: aspect_bazel_lib has all required fields"
        echo "    - version: $aspect_version"
        echo "    - minimum_version: $aspect_min"
        echo "    - urls count: $aspect_urls"
        echo "    - registry: $aspect_registry"
    else
        echo "  ✗ FAIL: aspect_bazel_lib missing some fields"
        ((failures++))
    fi
else
    echo "  ✗ FAIL: aspect_bazel_lib module not found in output"
    ((failures++))
fi

# Test 10: Check that version can differ from minimum_version (rules_python case)
echo "Test 10: Checking support for different minimum_version vs version"
if "$JQ" -e '.rules_python' "$OUTPUT_FILE" > /dev/null 2>&1; then
    python_version=$("$JQ" -r '.rules_python.version' "$OUTPUT_FILE")
    python_min=$("$JQ" -r '.rules_python.minimum_version' "$OUTPUT_FILE")
    
    echo "  rules_python: minimum_version=$python_min, version=$python_version"
    if [ -n "$python_version" ] && [ -n "$python_min" ]; then
        echo "  ✓ PASS: rules_python has both minimum_version and version (may differ)"
    else
        echo "  ✗ FAIL: rules_python missing version or minimum_version"
        ((failures++))
    fi
else
    echo "  ⚠ SKIP: rules_python not in test data"
fi

echo ""
if [ "$failures" -eq 0 ]; then
    echo "All field validation tests passed!"
    exit 0
else
    echo "$failures test(s) failed"
    exit 1
fi
