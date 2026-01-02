#!/usr/bin/env bash


test_output () {
    local output="$1"
    EXPECTED='{
        "artifact-linux-amd64.tar.gz":"869373d2d22ffccc022e2acbf0e1d337c5c553b3a2187a9067d84c0082f868ec",
        "artifact-darwin-arm64.tar.gz":"b798061bef81b227cbe7bfea791087cf877a3457685d971ca2a14ebfa67df6c4",
        "checksums.txt":"6d247fcf0e5346087f016c9ec43e29344e02ea12549214424d09676a9a76cb79",
        "artifact.deb":"21750c993876d9f213cebdf42266cfc92bc078c51be8e1e3eb8e7fe6790058fc"}'
    echo "$EXPECTED" | jq -c '.' > /tmp/expected
    echo "$output" | jq -c '.' > /tmp/output
    cmp -s /tmp/expected /tmp/output || {
        echo "fail:Output does not match" >> "$TEST_OUTPUT"
        diff -u /tmp/expected /tmp/output
        return
    }
    echo "success:Output matches" >> "$TEST_OUTPUT"
}

test_output_log () {
    EXPECTED='gh release view v1.0.0 --repo owner/repo --json assets --jq ".assets[] | {key: .name, value: .digest}"'
    echo "$EXPECTED" > /tmp/expected
    cmp -s /tmp/expected "$MOCK_LOG" || {
        echo "fail:Output log does not match" >> "$TEST_OUTPUT"
        diff -u /tmp/expected "$MOCK_LOG"
        return
    }
    echo "success:Output log matches" >> "$TEST_OUTPUT"

}
