#!/usr/bin/env bash


test_output () {
    local output="$1"
    EXPECTED='action-0.3.48'
    echo "$EXPECTED" > /tmp/expected
    echo "$output" > /tmp/output
    cmp -s /tmp/expected /tmp/output || {
        echo "fail:Output does not match" >> "$TEST_OUTPUT"
        diff -u /tmp/expected /tmp/output
        return
    }
    echo "success:Output matches" >> "$TEST_OUTPUT"
}

test_output_log () {
    EXPECTED='gh release list --repo owner/repo --limit 1 --json tagName --jq ".[0].tagName"'
    echo "$EXPECTED" > /tmp/expected
    cmp -s /tmp/expected "$MOCK_LOG" || {
        echo "fail:Output log does not match" >> "$TEST_OUTPUT"
        diff -u /tmp/expected "$MOCK_LOG"
        return
    }
    echo "success:Output log matches" >> "$TEST_OUTPUT"

}

test_pattern_output () {
    local output="$1"
    EXPECTED='bins-0.1.32'
    echo "$EXPECTED" > /tmp/expected
    echo "$output" > /tmp/output
    cmp -s /tmp/expected /tmp/output || {
        echo "fail:Pattern output does not match" >> "$TEST_OUTPUT"
        diff -u /tmp/expected /tmp/output
        return
    }
    echo "success:Pattern output matches" >> "$TEST_OUTPUT"
}

test_pattern_output_log () {
    EXPECTED='gh release list --repo owner/repo --limit 100 --json tagName --jq [.[]|select(.tagName|test("^bins-"))]|.[0].tagName'
    echo "$EXPECTED" > /tmp/expected
    cmp -s /tmp/expected "$MOCK_LOG" || {
        echo "fail:Pattern output log does not match" >> "$TEST_OUTPUT"
        diff -u /tmp/expected "$MOCK_LOG"
        return
    }
    echo "success:Pattern output log matches" >> "$TEST_OUTPUT"

}

test_limit_output_log () {
    EXPECTED='gh release list --repo owner/repo --limit 200 --json tagName --jq [.[]|select(.tagName|test("^bins-"))]|.[0].tagName'
    echo "$EXPECTED" > /tmp/expected
    cmp -s /tmp/expected "$MOCK_LOG" || {
        echo "fail:Limit output log does not match" >> "$TEST_OUTPUT"
        diff -u /tmp/expected "$MOCK_LOG"
        return
    }
    echo "success:Limit output log matches" >> "$TEST_OUTPUT"

}
