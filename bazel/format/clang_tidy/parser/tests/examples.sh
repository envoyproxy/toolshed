#!/bin/bash
# Example usage of the clang-tidy parser
# This script demonstrates various ways to use parse_clang_tidy.jq

set -euo pipefail

PARSER_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PARSER="${PARSER_DIR}/parse_clang_tidy.jq"
SAMPLE="${PARSER_DIR}/tests/sample_input.txt"

echo "Clang-tidy Parser Examples"
echo "==========================="
echo ""

# Example 1: Basic parsing
echo "Example 1: Basic parsing"
echo "------------------------"
cat "${SAMPLE}" | jq -Rf "${PARSER}" | jq -C '.' | head -30
echo ""
echo "..."
echo ""

# Example 2: Count diagnostics by severity
echo "Example 2: Count diagnostics by severity"
echo "-----------------------------------------"
cat "${SAMPLE}" | jq -Rf "${PARSER}" | \
  jq 'group_by(.severity) | map({severity: .[0].severity, count: length})'
echo ""

# Example 3: Filter only errors
echo "Example 3: Filter only errors"
echo "------------------------------"
cat "${SAMPLE}" | jq -Rf "${PARSER}" | \
  jq '[.[] | select(.severity == "error")]'
echo ""

# Example 4: Group by file
echo "Example 4: Group by file"
echo "------------------------"
cat "${SAMPLE}" | jq -Rf "${PARSER}" | \
  jq 'group_by(.file) | map({file: .[0].file, count: length})'
echo ""

# Example 5: Extract unique check names
echo "Example 5: Extract unique check names"
echo "--------------------------------------"
cat "${SAMPLE}" | jq -Rf "${PARSER}" | \
  jq '[.[].check] | unique | sort'
echo ""

# Example 6: Summary for CI
echo "Example 6: CI Summary"
echo "---------------------"
cat "${SAMPLE}" | jq -Rf "${PARSER}" | \
  jq '{
    total: length,
    errors: [.[] | select(.severity == "error")] | length,
    warnings: [.[] | select(.severity == "warning")] | length,
    notes: [.[] | select(.severity == "note")] | length,
    files: [.[].file] | unique | length,
    checks: [.[].check | select(. != "")] | unique | length
  }'
echo ""

# Example 7: Deduplicate by file, line, and message
echo "Example 7: Deduplicate by file, line, and message"
echo "--------------------------------------------------"
echo "Original count:"
cat "${SAMPLE}" | jq -Rf "${PARSER}" | jq 'length'
echo "After deduplication:"
cat "${SAMPLE}" | jq -Rf "${PARSER}" | \
  jq 'unique_by([.file, .line, .message]) | length'
echo ""

# Example 8: Format for human-readable output
echo "Example 8: Human-readable format"
echo "---------------------------------"
cat "${SAMPLE}" | jq -Rf "${PARSER}" | \
  jq -r '.[] | "\(.file):\(.line):\(.column): \(.severity): \(.message) [\(.check)]"' | head -5
echo ""

echo "Done!"
