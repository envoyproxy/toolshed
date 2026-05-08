#!/usr/bin/env bash

set -e -o pipefail


test_output_not_empty () {
    local output="${1}"
    if [[ -z "$output" ]]; then
        echo "fail:request action output is empty" >> "$TEST_OUTPUT"
        return
    fi
    echo "success:request action output is not empty" >> "$TEST_OUTPUT"
}

test_request_data () {
    local output="${1}"

    if ! TARGET_BRANCH="$(echo "$output" | jq -r '.request["target-branch"]')"; then
        echo "fail:unable to parse request.target-branch from action output" >> "$TEST_OUTPUT"
        return
    fi

    if [[ "$TARGET_BRANCH" != "main" ]]; then
        echo "fail:expected request.target-branch to be main, got $TARGET_BRANCH" >> "$TEST_OUTPUT"
    else
        echo "success:request.target-branch matches expected branch" >> "$TEST_OUTPUT"
    fi

    if ! VERSION_CHANGED="$(echo "$output" | jq -r '.request.version.changed')"; then
        echo "fail:unable to parse request.version.changed from action output" >> "$TEST_OUTPUT"
        return
    fi

    if [[ "$VERSION_CHANGED" != "false" ]]; then
        echo "fail:expected request.version.changed to be false, got $VERSION_CHANGED" >> "$TEST_OUTPUT"
    else
        echo "success:request.version.changed remains false when no files changed" >> "$TEST_OUTPUT"
    fi
}
