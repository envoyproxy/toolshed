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

JQ_ARGS=()
if [[ -n "${JQ_MODULES_DIR:-}" ]]; then
    JQ_ARGS+=("-L" "${JQ_MODULES_DIR}")
fi

$JQ_BIN "${JQ_ARGS[@]}" "${FILTER}" "${@}" < "$TARGET"
