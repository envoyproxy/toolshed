#!/usr/bin/env bash

# Stream stderr to the action log while emitting matching annotations.
set -euo pipefail

output="$1"

awk \
    -v output="$output" \
    -v error_match="${TOOLSHED_ERROR_MATCH:-}" \
    -v notice_match="${TOOLSHED_NOTICE_MATCH:-}" \
    -v warning_match="${TOOLSHED_WARNING_MATCH:-}" \
    '
function emit(level, message, key, escaped) {
    key = level SUBSEP message
    if (seen[key]) {
        return
    }
    seen[key] = 1
    if (emitted[level] < 9) {
        escaped = message
        gsub(/%/, "%25", escaped)
        gsub(/\r/, "%0D", escaped)
        printf "::%s::%s\n", level, escaped
        fflush()
        emitted[level]++
    } else {
        suppressed[level]++
    }
}

function match_and_emit(level, line, patterns, pattern_count, i, clean_line) {
    clean_line = line
    gsub(/\033\[[0-9;]*[a-zA-Z]/, "", clean_line)
    for (i = 1; i <= pattern_count; i++) {
        if (patterns[i] != "" && clean_line ~ patterns[i]) {
            emit(level, line)
            return
        }
    }
}

BEGIN {
    error_count = split(error_match, error_patterns, "\n")
    notice_count = split(notice_match, notice_patterns, "\n")
    warning_count = split(warning_match, warning_patterns, "\n")
}

{
    print $0 >> output
    fflush(output)
    print $0
    fflush()
    match_and_emit("notice", $0, notice_patterns, notice_count)
    match_and_emit("error", $0, error_patterns, error_count)
    match_and_emit("warning", $0, warning_patterns, warning_count)
}

END {
    for (i = 1; i <= 3; i++) {
        level = (i == 1 ? "notice" : i == 2 ? "error" : "warning")
        if (suppressed[level] > 0) {
            printf "::%s::... and %d more %ss\n", level, suppressed[level], level
        }
    }
}
'
