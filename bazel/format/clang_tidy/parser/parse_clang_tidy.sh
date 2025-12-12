#!/bin/bash
# Wrapper script for parse_clang_tidy.jq
# Makes it easier to use the parser from the command line

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PARSER="${SCRIPT_DIR}/parse_clang_tidy.jq"

# Check if jq is available
if ! command -v jq &> /dev/null; then
    echo "ERROR: jq is not installed" >&2
    echo "Please install jq: https://stedolan.github.io/jq/" >&2
    exit 1
fi

# Show help if requested
if [ "${1:-}" = "-h" ] || [ "${1:-}" = "--help" ]; then
    cat <<EOF
Usage: $(basename "$0") [OPTIONS] [FILE...]

Parse clang-tidy output and convert to JSON.

Options:
  -h, --help     Show this help message
  -c, --compact  Output compact JSON (one line per diagnostic)
  -s, --summary  Output summary statistics instead of full JSON
  -e, --errors   Filter to show only errors
  -w, --warnings Filter to show only warnings

Input:
  FILE           One or more files containing clang-tidy output
                 If no files specified, reads from stdin

Output:
  JSON array of diagnostic objects (default)
  Compact JSON (with -c)
  Summary statistics (with -s)

Examples:
  # Parse from stdin
  clang-tidy file.cpp | $(basename "$0")

  # Parse from file
  $(basename "$0") clang_tidy_output.txt

  # Get summary
  $(basename "$0") --summary clang_tidy_output.txt

  # Show only errors
  $(basename "$0") --errors clang_tidy_output.txt

  # Compact output
  $(basename "$0") --compact clang_tidy_output.txt
EOF
    exit 0
fi

# Parse options
COMPACT=false
SUMMARY=false
FILTER=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        -c|--compact)
            COMPACT=true
            shift
            ;;
        -s|--summary)
            SUMMARY=true
            shift
            ;;
        -e|--errors)
            FILTER="error"
            shift
            ;;
        -w|--warnings)
            FILTER="warning"
            shift
            ;;
        -*)
            echo "Unknown option: $1" >&2
            echo "Use -h or --help for usage information" >&2
            exit 1
            ;;
        *)
            break
            ;;
    esac
done

# Build jq pipeline
if [ -n "${FILTER}" ]; then
    FILTER_JQ="| [.[] | select(.severity == \"${FILTER}\")]"
else
    FILTER_JQ=""
fi

if [ "${SUMMARY}" = true ]; then
    SUMMARY_JQ="| {
        total: length,
        errors: [.[] | select(.severity == \"error\")] | length,
        warnings: [.[] | select(.severity == \"warning\")] | length,
        notes: [.[] | select(.severity == \"note\")] | length,
        files: [.[].file] | unique | length,
        checks: [.[].check | select(. != \"\")] | unique | length
    }"
else
    SUMMARY_JQ=""
fi

if [ "${COMPACT}" = true ]; then
    COMPACT_FLAG="-c"
else
    COMPACT_FLAG=""
fi

# Parse input
if [ $# -eq 0 ]; then
    # Read from stdin
    jq ${COMPACT_FLAG} -Rf "${PARSER}" | jq ${COMPACT_FLAG} ". ${FILTER_JQ} ${SUMMARY_JQ}"
else
    # Read from files
    for file in "$@"; do
        if [ ! -f "${file}" ]; then
            echo "ERROR: File not found: ${file}" >&2
            exit 1
        fi
        cat "${file}" | jq ${COMPACT_FLAG} -Rf "${PARSER}" | jq ${COMPACT_FLAG} ". ${FILTER_JQ} ${SUMMARY_JQ}"
    done
fi
