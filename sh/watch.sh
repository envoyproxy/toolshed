#!/usr/bin/env bash

set -e -o pipefail

WATCH_DIR="${1}"
COMMAND="${2}"

DEBUG=${DEBUG:-}
DEFAULT_IGNORE=${DEFAULT_IGNORE:-'(\.#|~$|/#|\.git)'}
IGNORE=${IGNORE:-}


WATCH_COMMAND=${WATCH_COMMAND:-}
WATCH_FS_COMMAND=${WATCH_FS_COMMAND:-}

DEBOUNCE_SLEEP="${DEBOUNCE_SLEEP:-0.1}"
FSWATCH_LATENCY="${FSWATCH_LATENCY:-0.05}"
RUN_ON_START="${RUN_ON_START:-}"


if [[ -n "$IGNORE" ]]; then
    IGNORE="(${DEFAULT_IGNORE}|${IGNORE})"
else
    IGNORE=$DEFAULT_IGNORE
fi

if [[ "$WATCH_COMMAND" == "inotify" ]]; then
    WATCH_FS_COMMAND=on_fs_change_inotify
elif [[ "$WATCH_COMMAND" == "fswatch" ]]; then
    WATCH_FS_COMMAND=on_fs_change_fswatch
fi

if [[ -z "$WATCH_FS_COMMAND" ]]; then
    if command -v inotifywait &> /dev/null; then
        WATCH_COMMAND=inotify
        WATCH_FS_COMMAND=on_fs_change_inotify
    elif command -v fswatch &> /dev/null; then
        WATCH_COMMAND=fswatch
        WATCH_FS_COMMAND=on_fs_change_fswatch
    else
        echo 'No FS notifier found! Install either inotify-tools or fswatch' >&2
        exit 1
    fi
fi

if [[ -z "$WATCH_DIR" ]]; then
    echo "No directory to watch specified!" >&2
    exit 1
fi

if [[ -z "$COMMAND" ]]; then
    echo "No command specified!" >&2
    exit 1
fi

FSWATCH_ARGS=(--latency="$FSWATCH_LATENCY")
if [[ "$(uname -s)" == "Linux" ]]; then
    FSWATCH_ARGS+=(-m inotify_monitor)
elif [[ "$(uname -s)" == "Darwin" ]]; then
    FSWATCH_ARGS+=(-m fsevents_monitor)
fi


_kill () {
    local pid=$1
    local children; children=$(pgrep -P "$pid" 2>/dev/null || echo "")

    # Recursively kill all children first
    for child in $children; do
        _kill "$child"
    done

    # Kill the main process
    kill "$pid" &>/dev/null || :
    wait "$pid" &>/dev/null || :
}


cleanup () {
    _kill "$$"
}


trap cleanup EXIT


_debug () {
    if [[ -n "$DEBUG" ]]; then
        echo "${@}" >&2
    fi
}


_log () {
    if [[ -z "$QUIET" ]]; then
        echo "${@}" >&2
    fi
}


on_fs_change_inotify () {
    inotifywait \
        -m -r -q \
        -e modify,create,delete,move \
        "${1}" \
        --format "%w%f" \
        --exclude "${2}"
}


on_fs_change_fswatch () {
    fswatch \
        -r -e "${2}" \
        "${FSWATCH_ARGS[@]}" \
        --event=Created \
        --event=Updated \
        --event=Removed \
        --event=Renamed \
        "${1}"
}


debounce() {
    sleep "$DEBOUNCE_SLEEP"
    while read -t 0 -r FILE; do
        read -r FILE
    done
}


run_command () {
    $COMMAND \
        && echo "command succeeded" \
            || echo "command failed!"
}


watch_fs () {
    if [[ -n "$RUN_ON_START" ]]; then
        echo "Start"
    fi
    "$WATCH_FS_COMMAND" "${@}"
}


watch_loop() {
   _log "Watching filesystem (${WATCH_COMMAND}):"
    _log "   path: ${WATCH_DIR}"
    _log "   ignore: ${IGNORE}"
    watch_fs "$WATCH_DIR" "$IGNORE" | while read -r FILE; do
        _debug "CHANGE: ${FILE}"
        debounce
        _debug "RUN: ${COMMAND}"
        run_command
    done
}


watch () {
    watch_loop
}


watch
