#!/usr/bin/env bash

set -e -o pipefail

TARGET=${1}
shift
FILTER=${1}

if [[ -z "$FILTER" ]]; then
    FILTER=.
else
    shift
fi

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

JQ_ARGS=()
if [[ -n "${JQ_MODULES_ROOT_MARKER:-}" ]]; then
    JQ_ARGS+=("-L" "$(dirname "$(_resolve_runfile "${JQ_MODULES_ROOT_MARKER}")")")
elif [[ -n "${JQ_MODULES_DIR:-}" ]]; then
    JQ_ARGS+=("-L" "${JQ_MODULES_DIR}")
fi

$JQ_BIN "${JQ_ARGS[@]}" "${FILTER}" "${@}" < "$TARGET"
