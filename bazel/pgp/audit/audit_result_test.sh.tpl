#!/usr/bin/env bash
set -euo pipefail

resolve_runfile() {
    local path="$1"
    if [[ -n "${RUNFILES_DIR:-}" && -e "${RUNFILES_DIR}/${path}" ]]; then
        printf '%s\n' "${RUNFILES_DIR}/${path}"
        return 0
    fi
    if [[ -e "$0.runfiles/${path}" ]]; then
        printf '%s\n' "$0.runfiles/${path}"
        return 0
    fi
    printf 'runfile not found: %s\n' "${path}" >&2
    return 1
}

report="$(resolve_runfile @REPORT@)"
status="$(resolve_runfile @STATUS@)"
cat "$report"
exit "$(cat "$status")"
