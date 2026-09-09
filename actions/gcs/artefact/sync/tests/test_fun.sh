#!/usr/bin/env bash

# Test helper functions for the gcs/artefact/sync action tests

VALIDATE_SH="${ACTION_TEST_PATH}/../validate.sh"

test_mock_log_contains() {
    local expected="${1}"
    local description="${2:-gcloud invocation}"

    if grep -qF -- "$expected" "$MOCK_LOG"; then
        echo "success:${description} found: ${expected}" >> "$TEST_OUTPUT"
        return 0
    fi
    echo "fail:${description} not found: ${expected}" >> "$TEST_OUTPUT"
    return 1
}

test_validate_accepts() {
    local description="${1}"
    shift

    if "$VALIDATE_SH" "$@" > /dev/null 2>&1; then
        echo "success:validation accepted ${description}" >> "$TEST_OUTPUT"
        return 0
    fi
    echo "fail:validation rejected ${description}" >> "$TEST_OUTPUT"
    return 1
}

test_validate_rejects() {
    local description="${1}"
    shift

    if "$VALIDATE_SH" "$@" > /dev/null 2>&1; then
        echo "fail:validation accepted ${description}" >> "$TEST_OUTPUT"
        return 1
    fi
    echo "success:validation rejected ${description}" >> "$TEST_OUTPUT"
    return 0
}
