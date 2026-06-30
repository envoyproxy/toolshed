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

test_status_has () {
    local output="$1"
    local workflow="$2"
    local field="$3"
    local expected="$4"
    local got
    got=$(echo "$output" | jq -r --arg w "$workflow" --arg f "$field" \
        '.status | fromjson | .[$w][$f]')
    if [[ "$got" != "$expected" ]]; then
        echo "fail:Expected status[$workflow][$field]='$expected', got '$got'" >> "$TEST_OUTPUT"
        return
    fi
    echo "success:status[$workflow][$field]=$got" >> "$TEST_OUTPUT"
}

test_status_missing () {
    local output="$1"
    local workflow="$2"
    local present
    present=$(echo "$output" | jq -r --arg w "$workflow" \
        '.status | fromjson | has($w)')
    if [[ "$present" != "false" ]]; then
        echo "fail:Expected workflow '$workflow' to be absent from status, got present=$present" \
            >> "$TEST_OUTPUT"
        return
    fi
    echo "success:workflow '$workflow' correctly absent from status" >> "$TEST_OUTPUT"
}
