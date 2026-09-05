#!/usr/bin/env bash

test_output_contains() {
    local value="${1}"
    local expected="${2}"
    local description="${3:-Output contains: ${expected}}"

    if [[ "$value" == *"$expected"* ]]; then
        echo "success:${description}" >> "${TEST_OUTPUT}"
        return 0
    fi
    echo "fail:${description}" >> "${TEST_OUTPUT}"
    return 1
}
