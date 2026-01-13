#!/usr/bin/env bash

set -e -o pipefail


test_tarball_exists () {
    local tarball="${1}"
    if [[ -z "$tarball" ]]; then
        echo "fail:Tarball output is empty" >> "$TEST_OUTPUT"
        return
    fi
    if [[ ! -f "$tarball" ]]; then
        echo "fail:Tarball not created: $tarball" >> "$TEST_OUTPUT"
        return
    fi
    echo "success:Tarball created successfully: $tarball" >> "$TEST_OUTPUT"
}

test_tarball_content () {
    local tarball="${1}"
    local expected_pattern="${2}"

    if [[ -z "$tarball" ]]; then
        echo "fail:Tarball parameter is empty" >> "$TEST_OUTPUT"
        return
    fi

    # List contents of tarball
    if ! tar -tzf "$tarball" | head -5 > /tmp/tarball_contents.txt; then
        echo "fail:Failed to list tarball contents" >> "$TEST_OUTPUT"
        return
    fi

    # Check if expected pattern exists in contents
    if grep -q "$expected_pattern" /tmp/tarball_contents.txt; then
        echo "success:Tarball contains expected pattern: $expected_pattern" >> "$TEST_OUTPUT"
    else
        echo "fail:Tarball does not contain expected pattern: $expected_pattern" >> "$TEST_OUTPUT"
        cat /tmp/tarball_contents.txt
        return
    fi
}

test_version_output () {
    local version="${1}"
    local expected="${2}"

    if [[ -z "$version" ]]; then
        echo "fail:Version output is empty" >> "$TEST_OUTPUT"
        return
    fi

    if [[ "$version" != "$expected" ]]; then
        echo "fail:Wrong version. Expected '$expected', got '$version'" >> "$TEST_OUTPUT"
        return
    fi

    echo "success:Version output correct: $version" >> "$TEST_OUTPUT"
}
