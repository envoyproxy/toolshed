
test_checkout () {
    if [[ ! -d ".git" ]]; then
        echo "fail:Repository not checked out (.git directory missing)" >> $TEST_OUTPUT
        return
    fi
    echo "success:Repository checked out successfully" >> $TEST_OUTPUT
}

test_repository () {
    # Verify we're in the right repository
    local expected_repo="${1}"
    current_repo=$(git config --get remote.origin.url | sed 's/.*github.com[:/]//' | sed 's/.git$//')
    if [[ "$current_repo" != "$expected_repo" ]]; then
        echo "fail:Wrong repository. Expected '$expected_repo', got '$current_repo'" >> $TEST_OUTPUT
        return
    fi
    echo "success:Correct repository: $current_repo" >> $TEST_OUTPUT
}

test_branch () {
    # Verify branch
    output_branch=${1}
    expected_branch=${2}
    if [[ -z "$output_branch" ]]; then
        echo "fail: branch-name output is empty" >> $TEST_OUTPUT
        return
    fi
    if [[ "$expected_branch" != "$output_branch" ]]; then
        echo "fail:Wrong branch. Expected '$expected_branch', got '$output_branch'" >> $TEST_OUTPUT
        return
    fi
    echo "success:branch-name output: $output_branch" >> $TEST_OUTPUT
}
