#!/usr/bin/env bash

# Test helpers for actions/buildah tests.
# Writes "success:..." / "fail:..." lines to $TEST_OUTPUT.


# Count how many buildah calls appear in $MOCK_LOG.
test_mock_call_count() {
    local expected="${1}"
    local count
    count=$(grep -c "^buildah " "${MOCK_LOG}" 2>/dev/null || echo 0)
    if [[ "${count}" -eq "${expected}" ]]; then
        echo "success:buildah call count is ${expected}" >> "${TEST_OUTPUT}"
    else
        echo "fail:Expected ${expected} buildah calls, got ${count}" >> "${TEST_OUTPUT}"
        echo "--- MOCK_LOG ---" >&2
        cat "${MOCK_LOG}" >&2
    fi
}

# Assert at least one line in $MOCK_LOG matches the given extended regex.
test_mock_log_contains() {
    local pattern="${1}"
    local description="${2:-log contains: ${pattern}}"
    if grep -qE "${pattern}" "${MOCK_LOG}" 2>/dev/null; then
        echo "success:${description}" >> "${TEST_OUTPUT}"
    else
        echo "fail:${description}" >> "${TEST_OUTPUT}"
        echo "--- MOCK_LOG ---" >&2
        cat "${MOCK_LOG}" >&2
    fi
}

# Assert no line in $MOCK_LOG matches the given extended regex.
test_mock_log_not_contains() {
    local pattern="${1}"
    local description="${2:-log does not contain: ${pattern}}"
    if grep -qE "${pattern}" "${MOCK_LOG}" 2>/dev/null; then
        echo "fail:${description}" >> "${TEST_OUTPUT}"
        echo "--- MOCK_LOG ---" >&2
        cat "${MOCK_LOG}" >&2
    else
        echo "success:${description}" >> "${TEST_OUTPUT}"
    fi
}

# Assert the captured step outcome (written by the failure-test bash-postfix).
# Reads /tmp/buildah-test-rc; expected is "success" or "failure".
test_step_outcome() {
    local expected="${1}"
    local rc_file="/tmp/buildah-test-rc"
    local rc=0
    [[ -f "${rc_file}" ]] && rc=$(cat "${rc_file}")

    local outcome="success"
    [[ "${rc}" -ne 0 ]] && outcome="failure"

    if [[ "${outcome}" == "${expected}" ]]; then
        echo "success:step outcome is ${expected} (rc=${rc})" >> "${TEST_OUTPUT}"
    else
        echo "fail:Expected step outcome '${expected}', got '${outcome}' (rc=${rc})" >> "${TEST_OUTPUT}"
    fi
}
