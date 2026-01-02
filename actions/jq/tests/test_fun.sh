#!/usr/bin/env bash

# Test helper functions for jq GitHub action tests

test_output_not_empty() {
    local output="${1}"
    local description="${2:-jq output}"

    if [[ -z "$output" ]]; then
        echo "fail:${description} is empty" >> "$TEST_OUTPUT"
        return 1
    else
        echo "success:${description} is not empty" >> "$TEST_OUTPUT"
        return 0
    fi
}

test_output_equals() {
    local output="${1}"
    local expected="${2}"
    local description="${3:-Value}"

    if [[ "$output" != "$expected" ]]; then
        echo "fail:${description}: expected '${expected}', got '${output}'" >> "$TEST_OUTPUT"
        return 1
    else
        echo "success:${description} is correct: ${output}" >> "$TEST_OUTPUT"
        return 0
    fi
}

test_json_key() {
    local json="${1}"
    local key="${2}"
    local expected="${3}"
    local description="${4:-Key \"${key}\"}"

    local value
    value=$(echo "$json" | jq -r ".${key}")

    if [[ "$value" != "$expected" ]]; then
        echo "fail:${description}: expected '${expected}', got '${value}'" >> "$TEST_OUTPUT"
        return 1
    else
        echo "success:${description} is correct: ${value}" >> "$TEST_OUTPUT"
        return 0
    fi
}

test_json_array_item() {
    local json="${1}"
    local index="${2}"
    local expected="${3}"
    local description="${4:-Array item [${index}]}"

    local value
    value=$(echo "$json" | jq -r ".[${index}]")

    if [[ "$value" != "$expected" ]]; then
        echo "fail:${description}: expected '${expected}', got '${value}'" >> "$TEST_OUTPUT"
        return 1
    else
        echo "success:${description} is correct: ${value}" >> "$TEST_OUTPUT"
        return 0
    fi
}

test_base64_decoded() {
    local encoded="${1}"
    local expected="${2}"
    local description="${3:-Decoded value}"

    local decoded
    decoded=$(echo "$encoded" | base64 -d)

    if [[ "$decoded" != "$expected" ]]; then
        echo "fail:${description}: expected '${expected}', got '${decoded}'" >> "$TEST_OUTPUT"
        return 1
    else
        echo "success:${description} is correct: ${decoded}" >> "$TEST_OUTPUT"
        return 0
    fi
}

test_is_base64_encoded() {
    local value="${1}"
    local original="${2}"
    local description="${3:-Output}"

    if [[ "$value" == "$original" ]]; then
        echo "fail:${description} was not base64 encoded" >> "$TEST_OUTPUT"
        return 1
    else
        echo "success:${description} was base64 encoded" >> "$TEST_OUTPUT"
        return 0
    fi
}

test_env_var_set() {
    local var_name="${1}"
    local expected="${2}"
    local description="${3:-Environment variable ${var_name}}"

    local value="${!var_name}"

    if [[ -z "$value" ]]; then
        echo "fail:${description} not set" >> "$TEST_OUTPUT"
        return 1
    fi

    echo "success:${description} is set: ${value}" >> "$TEST_OUTPUT"

    if [[ -n "$expected" && "$value" != "$expected" ]]; then
        echo "fail:${description}: expected '${expected}', got '${value}'" >> "$TEST_OUTPUT"
        return 1
    elif [[ -n "$expected" ]]; then
        echo "success:${description} value is correct: ${value}" >> "$TEST_OUTPUT"
    fi

    return 0
}

test_file_exists() {
    local path="${1}"
    local description="${2:-File ${path}}"

    if [[ ! -f "$path" ]]; then
        echo "fail:${description} not found" >> "$TEST_OUTPUT"
        return 1
    else
        echo "success:${description} exists" >> "$TEST_OUTPUT"
        return 0
    fi
}

test_file_content() {
    local path="${1}"
    local expected="${2}"
    local description="${3:-File content}"

    if [[ ! -f "$path" ]]; then
        echo "fail:${description}: file not found at ${path}" >> "$TEST_OUTPUT"
        return 1
    fi

    local content
    content=$(cat "$path")

    if [[ "$content" != "$expected" ]]; then
        echo "fail:${description}: expected '${expected}', got '${content}'" >> "$TEST_OUTPUT"
        return 1
    else
        echo "success:${description} is correct: ${content}" >> "$TEST_OUTPUT"
        return 0
    fi
}
