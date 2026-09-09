#!/usr/bin/env bash

# Test helper functions for the github/env/summary action tests

test_file_contains() {
    local path="${1}"
    local expected="${2}"
    local description="${3:-File ${path}}"

    if [[ ! -f "$path" ]]; then
        echo "fail:${description}: file not found at ${path}" >> "$TEST_OUTPUT"
        return 1
    fi
    if grep -qF -- "$expected" "$path"; then
        echo "success:${description} contains: ${expected}" >> "$TEST_OUTPUT"
        return 0
    fi
    echo "fail:${description} does not contain: ${expected}" >> "$TEST_OUTPUT"
    return 1
}

test_file_not_contains() {
    local path="${1}"
    local unexpected="${2}"
    local description="${3:-File ${path}}"

    if [[ ! -f "$path" ]]; then
        echo "fail:${description}: file not found at ${path}" >> "$TEST_OUTPUT"
        return 1
    fi
    if grep -qF -- "$unexpected" "$path"; then
        echo "fail:${description} contains: ${unexpected}" >> "$TEST_OUTPUT"
        return 1
    fi
    echo "success:${description} does not contain: ${unexpected}" >> "$TEST_OUTPUT"
    return 0
}
