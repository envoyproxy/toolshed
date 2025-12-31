#!/usr/bin/env bash


test_output () {
    local output="$1"
    local expected="$2"
    echo "$expected" > /tmp/expected
    echo "$output" > /tmp/output
    cmp -s /tmp/expected /tmp/output || {
        echo "fail:Output does not match" >> "$TEST_OUTPUT"
        diff -u /tmp/expected /tmp/output
        return
    }
    echo "success:Output matches" >> "$TEST_OUTPUT"
}

test_output_log () {
    local limit="$1"
    local jqfilter="$2"
    EXPECTED="gh release list --repo owner/repo --limit ${limit} --json tagName --jq ${jqfilter}.[0].tagName"
    echo "$EXPECTED" > /tmp/expected
    cmp -s /tmp/expected "$MOCK_LOG" || {
        echo "fail:Output log does not match" >> "$TEST_OUTPUT"
        diff -u /tmp/expected "$MOCK_LOG"
        return
    }
    echo "success:Output log matches" >> "$TEST_OUTPUT"

}
