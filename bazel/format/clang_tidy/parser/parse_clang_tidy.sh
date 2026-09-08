#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

_resolve_runfile () {
    local value="$1"
    if [[ -n "${value}" && "${value}" != /* ]]; then
        local f=bazel_tools/tools/bash/runfiles/runfiles.bash
        if [[ -z "${RUNFILES_DIR:-}" && -n "${TEST_SRCDIR:-}" ]]; then
            RUNFILES_DIR="${TEST_SRCDIR}"
        fi
        local runfiles_bash_path="${RUNFILES_DIR:-/dev/null}/$f"
        # shellcheck disable=SC1090
        source "${runfiles_bash_path}" 2>/dev/null || \
            source "$(grep -sm1 "^$f " "${RUNFILES_MANIFEST_FILE:-/dev/null}" | cut -f2 -d' ')" 2>/dev/null || \
            { echo >&2 "ERROR: cannot find runfiles.bash"; exit 1; }
        rlocation "${value}"
    else
        printf '%s\n' "${value}"
    fi
}

if [[ -n "${JQ_BIN:-}" ]]; then
    JQ_BIN="$(_resolve_runfile "${JQ_BIN}")"
fi
JQ="${JQ_BIN:-jq}"

# JQ_MODULES_ROOT_MARKER (set eg via Bazel to
# `$(rlocationpath @envoy_toolshed_jq//:modules_root.marker)`) locates the
# `envoy_toolshed_jq` modules directory so `clang/tidy` can be imported.
# Outside Bazel, it defaults to the `jq/` directory at the repo root.
if [[ -n "${JQ_MODULES_ROOT_MARKER:-}" ]]; then
    MODULES_ROOT="$(dirname "$(_resolve_runfile "${JQ_MODULES_ROOT_MARKER}")")"
else
    MODULES_ROOT="$(cd "${SCRIPT_DIR}/../../../../jq" && pwd)"
fi
PARSER='import "clang/tidy" as tidy; tidy::parse'

if ! command -v "$JQ" &> /dev/null; then
    echo "jq binary not found: ${JQ}" >&2
    exit 1
fi

if [ "${1:-}" = "-h" ] || [ "${1:-}" = "--help" ]; then
    cat <<EOF
Usage: $(basename "$0") [OPTIONS] [FILE...]
Parse clang-tidy output and convert to JSON.
Options:
  -h, --help     Show this help message
  -c, --compact  Output compact JSON
  -s, --summary  Output summary statistics
  -e, --errors   Filter to show only errors
  -w, --warnings Filter to show only warnings
Input:
  FILE           Files containing clang-tidy output (or stdin)
EOF
    exit 0
fi

COMPACT=false
SUMMARY=false
FILTER=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        -c|--compact) COMPACT=true; shift ;;
        -s|--summary) SUMMARY=true; shift ;;
        -e|--errors) FILTER="error"; shift ;;
        -w|--warnings) FILTER="warning"; shift ;;
        -*) echo "Unknown option: $1" >&2; exit 1 ;;
        *) break ;;
    esac
done

FILTER_JQ=""
if [ -n "${FILTER}" ]; then
    FILTER_JQ="| [.[] | select(.severity == \"${FILTER}\")]"
fi

SUMMARY_JQ=""
if [ "${SUMMARY}" = true ]; then
    SUMMARY_JQ="| {total: length, errors: [.[] | select(.severity == \"error\")] | length, warnings: [.[] | select(.severity == \"warning\")] | length, notes: [.[] | select(.severity == \"note\")] | length, files: [.[].file] | unique | length, checks: [.[].check | select(. != \"\")] | unique | length}"
fi

COMPACT_FLAG=""
if [ "${COMPACT}" = true ]; then
    COMPACT_FLAG="-c"
fi

if [ $# -eq 0 ]; then
    ${JQ} ${COMPACT_FLAG} -R -L "${MODULES_ROOT}" "${PARSER}" | ${JQ} ${COMPACT_FLAG} ". ${FILTER_JQ} ${SUMMARY_JQ}"
else
    for file in "$@"; do
        if [ ! -f "${file}" ]; then
            echo "ERROR: File not found: ${file}" >&2
            exit 1
        fi
        ${JQ} ${COMPACT_FLAG} -R -L "${MODULES_ROOT}" "${PARSER}" < "${file}" | ${JQ} ${COMPACT_FLAG} ". ${FILTER_JQ} ${SUMMARY_JQ}"
    done
fi

