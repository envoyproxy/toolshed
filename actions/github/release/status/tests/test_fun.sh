#!/usr/bin/env bash


test_continue () {
    local output="$1"
    local expected="$2"
    local got
    got=$(echo "$output" | jq -r '.continue')
    if [[ "$got" != "$expected" ]]; then
        echo "fail:Expected continue='$expected', got '$got'" >> "$TEST_OUTPUT"
        return
    fi
    echo "success:continue=$got" >> "$TEST_OUTPUT"
}

test_is_dev () {
    local output="$1"
    local expected="$2"
    local got
    got=$(echo "$output" | jq -r '.is_dev')
    if [[ "$got" != "$expected" ]]; then
        echo "fail:Expected is_dev='$expected', got '$got'" >> "$TEST_OUTPUT"
        return
    fi
    echo "success:is_dev=$got" >> "$TEST_OUTPUT"
}
