#!/usr/bin/env bash

set -e -o pipefail

WATCH_DIR="${1}"
COMMAND="${2}"

WATCH_LOCK_DIR="$(mktemp -d)"
WATCH_LOCK="${WATCH_LOCK_DIR}/lock"
DEBUG=${DEBUG:-}
IGNORE=${IGNORE:-'(\.#|~$|/#)'}

export WATCH_LOCK

WATCH_COMMAND=${WATCH_COMMAND:-}
WATCH_LOCK_COMMAND=${WATCH_LOCK_COMMAND:-}
WATCH_FS_COMMAND=${WATCH_FS_COMMAND:-}


if [[ "$WATCH_COMMAND" == "INOTIFY" ]]; then
    WATCH_FS_COMMAND=on_fs_change_inotify
    WATCH_LOCK_COMMAND=on_command_triggered_inotify
elif [[ "$WATCH_COMMAND" == "FSWATCH" ]]; then
    WATCH_FS_COMMAND=on_fs_change_fswatch
    WATCH_LOCK_COMMAND=on_command_triggered_fswatch
fi

if [[ -z "$WATCH_FS_COMMAND" ]]; then
    if command -v inotifywait &> /dev/null; then
        WATCH_FS_COMMAND=on_fs_change_inotify
    elif command -v fswatch &> /dev/null; then
        WATCH_FS_COMMAND=on_fs_change_fswatch
    else
        echo "No FS notifier found!" >&2
        exit 1
    fi
fi

if [[ -z "$WATCH_LOCK_COMMAND" ]]; then
    if command -v inotifywait &> /dev/null; then
        WATCH_LOCK_COMMAND=on_command_triggered_inotify
    elif command -v fswatch &> /dev/null; then
        WATCH_LOCK_COMMAND=on_command_triggered_fswatch
    else
        echo "No FS notifier found!" >&2
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

FSWATCH_ARGS=(--latency=0.1)
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
    rm -rf "$WATCH_LOCK_DIR"
}

trap cleanup EXIT


debug () {
    if [[ -n "$DEBUG" ]]; then
        echo "${@}" >&2
    fi
}


on_command_triggered_inotify () {
    debug "WATCH FS LOCK (inotify): ${1}"
    inotifywait \
        -m -r -q \
        -e create \
        "${1}" \
        --format "%w%f"
}


on_command_triggered_fswatch () {
    debug "WATCH FS LOCK (fswatch): ${1}"
    fswatch \
        -r \
        --event-flags \
        "${FSWATCH_ARGS[@]}" \
        --event=Created \
        "${1}"
}


on_fs_change_inotify () {
    debug "WATCH FS (inotify): ${1}"
    inotifywait \
        -m -r -q \
        -e modify,create,delete,move \
        "${1}" \
        --format "%w%f" \
        --exclude "${2}"
}


on_fs_change_fswatch () {
    debug "WATCH FS (fswatch): ${1}"
    fswatch \
        -r -e "${2}" \
        --event-flags \
        --event-flag-separator=/ \
        "${FSWATCH_ARGS[@]}" \
        --event=Created \
        --event=Updated \
        --event=Removed \
        --event=Renamed \
        "${1}"
}


command_loop() {
    "$WATCH_LOCK_COMMAND" "$WATCH_LOCK_DIR" | while read -r FILE; do
        if [[ ! -e "$WATCH_LOCK_DIR" ]]; then
            exit 0
        fi
        event=$(echo "$FILE" | cut -d' ' -f2)
        filename=$(echo "$FILE" | cut -d' ' -f1)
        if [[ -d "$filename" ]]; then
            continue
        fi
        if [[ ! -e "$WATCH_LOCK" ]]; then
            continue
        fi
        debug "RUN (${event}): ${filename}"
        sleep .1
        if [[ ! -e "$WATCH_LOCK_DIR" ]]; then
            exit 0
        fi
        rm -f "$WATCH_LOCK"
        $COMMAND &> /dev/null || echo "command failed!"
    done
}


watch_loop() {
    "$WATCH_FS_COMMAND" "$WATCH_DIR" "$IGNORE" | while read -r FILE; do
        if [[ ! -e "$WATCH_LOCK_DIR" ]]; then
            exit 0
        fi
        event=$(echo "$FILE" | cut -d' ' -f2)
        filename=$(echo "$FILE" | cut -d' ' -f1)
        debug "NOTIFIED (${event}): ${filename}"
        touch "$WATCH_LOCK"
    done
}


watch () {
    command_loop &
    watch_loop
}

watch
