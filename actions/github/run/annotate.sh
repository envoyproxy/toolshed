#!/usr/bin/env bash

# The run action captures command output through a streaming filter. Annotating in this
# stream keeps the workflow command next to the output that caused it.

TOOLSHED_ANNOTATION_SEEN_LEVEL=()
TOOLSHED_ANNOTATION_SEEN_MESSAGE=()
TOOLSHED_ANNOTATION_NOTICE_EMITTED=0
TOOLSHED_ANNOTATION_NOTICE_SUPPRESSED=0
TOOLSHED_ANNOTATION_ERROR_EMITTED=0
TOOLSHED_ANNOTATION_ERROR_SUPPRESSED=0
TOOLSHED_ANNOTATION_WARNING_EMITTED=0
TOOLSHED_ANNOTATION_WARNING_SUPPRESSED=0

toolshed_annotation_message() {
    local message="$1"
    message="${message//%/%25}"
    message="${message//$'\r'/%0D}"
    message="${message//$'\n'/%0A}"
    printf '%s' "$message"
}

toolshed_annotation_emit() {
    local level="$1"
    local message="$2"
    local i

    for i in "${!TOOLSHED_ANNOTATION_SEEN_LEVEL[@]}"; do
        if [[ "${TOOLSHED_ANNOTATION_SEEN_LEVEL[$i]}" == "$level" ]] && [[ "${TOOLSHED_ANNOTATION_SEEN_MESSAGE[$i]}" == "$message" ]]; then
            return
        fi
    done
    TOOLSHED_ANNOTATION_SEEN_LEVEL+=("$level")
    TOOLSHED_ANNOTATION_SEEN_MESSAGE+=("$message")

    local emitted
    local suppressed
    case "$level" in
        notice)
            emitted="$TOOLSHED_ANNOTATION_NOTICE_EMITTED"
            suppressed="$TOOLSHED_ANNOTATION_NOTICE_SUPPRESSED"
            ;;
        error)
            emitted="$TOOLSHED_ANNOTATION_ERROR_EMITTED"
            suppressed="$TOOLSHED_ANNOTATION_ERROR_SUPPRESSED"
            ;;
        warning)
            emitted="$TOOLSHED_ANNOTATION_WARNING_EMITTED"
            suppressed="$TOOLSHED_ANNOTATION_WARNING_SUPPRESSED"
            ;;
        *) return 0 ;;
    esac

    if [[ "$emitted" -lt 9 ]]; then
        printf '::%s::%s\n' "$level" "$(toolshed_annotation_message "$message")"
        emitted=$((emitted + 1))
    else
        suppressed=$((suppressed + 1))
    fi

    case "$level" in
        notice)
            TOOLSHED_ANNOTATION_NOTICE_EMITTED="$emitted"
            TOOLSHED_ANNOTATION_NOTICE_SUPPRESSED="$suppressed"
            ;;
        error)
            TOOLSHED_ANNOTATION_ERROR_EMITTED="$emitted"
            TOOLSHED_ANNOTATION_ERROR_SUPPRESSED="$suppressed"
            ;;
        warning)
            TOOLSHED_ANNOTATION_WARNING_EMITTED="$emitted"
            TOOLSHED_ANNOTATION_WARNING_SUPPRESSED="$suppressed"
            ;;
    esac
}

toolshed_annotation_match() {
    local level="$1"
    local line="$2"
    local patterns

    case "$level" in
        error) patterns="${TOOLSHED_ERROR_MATCH:-}" ;;
        warning) patterns="${TOOLSHED_WARNING_MATCH:-}" ;;
        notice) patterns="${TOOLSHED_NOTICE_MATCH:-}" ;;
        *) return 0 ;;
    esac

    while IFS= read -r pattern; do
        [[ -z "$pattern" ]] && continue
        if [[ "$line" =~ $pattern ]]; then
            toolshed_annotation_emit "$level" "$line"
            return
        fi
    done <<< "$patterns"
}

toolshed_annotate_stream() {
    local output="$1"

    while IFS= read -r line || [[ -n "$line" ]]; do
        printf '%s\n' "$line" >> "$output"
        printf '%s\n' "$line"
        toolshed_annotation_match notice "$line"
        toolshed_annotation_match error "$line"
        toolshed_annotation_match warning "$line"
    done

    for level in notice error warning; do
        local suppressed
        case "$level" in
            notice) suppressed="$TOOLSHED_ANNOTATION_NOTICE_SUPPRESSED" ;;
            error) suppressed="$TOOLSHED_ANNOTATION_ERROR_SUPPRESSED" ;;
            warning) suppressed="$TOOLSHED_ANNOTATION_WARNING_SUPPRESSED" ;;
        esac
        if [[ "$suppressed" -gt 0 ]]; then
            printf '::%s::%s\n' "$level" "... and $suppressed more ${level}s"
        fi
    done
}
toolshed_annotate_stream "$1"
