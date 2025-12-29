#!/usr/bin/env bash

# Test helper functions for github/pr action tests
# Mocking is done via separate scripts in mocks/ directory

test_branch_created() {
    local expected_branch="${1}"
    local current_branch
    current_branch=$(command git branch --show-current)

    if [[ "$current_branch" != "$expected_branch" ]]; then
        echo "fail:Wrong branch. Expected '$expected_branch', got '$current_branch'" >> "$TEST_OUTPUT"
        return
    fi
    echo "success:Branch created successfully: $current_branch" >> "$TEST_OUTPUT"
}

test_git_push_not_called() {
    # For dry-run tests, git push should not be called at all
    if grep -q "git push" /tmp/git-calls.log 2>/dev/null; then
        echo "fail:git push was called but shouldn't have been (dry-run)" >> "$TEST_OUTPUT"
        return
    fi
    echo "success:git push was not called (dry-run successful)" >> "$TEST_OUTPUT"
}

test_git_push_called() {
    # For non-dry-run tests, git push should be called (and mocked)
    if ! grep -q "git push" /tmp/git-calls.log 2>/dev/null; then
        echo "fail:git push was not called" >> "$TEST_OUTPUT"
        return
    fi
    echo "success:git push was called (mocked)" >> "$TEST_OUTPUT"
}

test_gh_not_called() {
    # For dry-run tests, gh pr create should not be called
    if grep -q "gh pr create" /tmp/gh-calls.log 2>/dev/null; then
        echo "fail:gh pr create was called but shouldn't have been (dry-run)" >> "$TEST_OUTPUT"
        return
    fi
    echo "success:gh pr create was not called (dry-run successful)" >> "$TEST_OUTPUT"
}

test_gh_called() {
    # For non-dry-run tests, gh pr create should be called (and mocked)
    if ! grep -q "gh pr create" /tmp/gh-calls.log 2>/dev/null; then
        echo "fail:gh pr create was not called" >> "$TEST_OUTPUT"
        return
    fi
    echo "success:gh pr create was called (mocked)" >> "$TEST_OUTPUT"
}

test_no_commit_made() {
    # Check if HEAD commit message matches what we expect (no new commit)
    local expected_message="${1}"
    local actual_message
    actual_message=$(git log -1 --pretty=%s)

    if [[ "$actual_message" == "$expected_message" ]]; then
        echo "fail:Unexpected commit was made with message: $actual_message" >> "$TEST_OUTPUT"
        return
    fi
    echo "success:No new commit was made as expected" >> "$TEST_OUTPUT"
}

test_commit_made() {
    local expected_message="${1}"
    local actual_message
    actual_message=$(command git log -1 --pretty=%s)

    if [[ "$actual_message" != "$expected_message" ]]; then
        echo "fail:Wrong commit message. Expected '$expected_message', got '$actual_message'" >> "$TEST_OUTPUT"
        return
    fi
    echo "success:Commit made with correct message: $actual_message" >> "$TEST_OUTPUT"
}

test_git_user_config() {
    local expected_name="${1}"
    local expected_email="${2}"
    local actual_name
    local actual_email

    actual_name=$(command git config --global user.name)
    actual_email=$(command git config --global user.email)

    if [[ "$actual_name" != "$expected_name" ]]; then
        echo "fail:Wrong git user.name. Expected '$expected_name', got '$actual_name'" >> "$TEST_OUTPUT"
        return
    fi
    if [[ "$actual_email" != "$expected_email" ]]; then
        echo "fail:Wrong git user.email. Expected '$expected_email', got '$actual_email'" >> "$TEST_OUTPUT"
        return
    fi
    echo "success:Git user config set correctly: $actual_name <$actual_email>" >> "$TEST_OUTPUT"
}

test_working_directory() {
    local expected_dir="${1}"
    local current_dir
    current_dir=$(pwd)

    if [[ ! "$current_dir" =~ $expected_dir$ ]]; then
        echo "fail:Wrong working directory. Expected to end with '$expected_dir', got '$current_dir'" >> "$TEST_OUTPUT"
        return
    fi
    echo "success:Working directory correct: $current_dir" >> "$TEST_OUTPUT"
}

test_file_exists() {
    local file="${1}"

    if [[ ! -f "$file" ]]; then
        echo "fail:File does not exist: $file" >> "$TEST_OUTPUT"
        return
    fi
    echo "success:File exists: $file" >> "$TEST_OUTPUT"
}

test_file_contains() {
    local file="${1}"
    local pattern="${2}"

    if [[ ! -f "$file" ]]; then
        echo "fail:File does not exist: $file" >> "$TEST_OUTPUT"
        return
    fi

    if ! grep -q "$pattern" "$file"; then
        echo "fail:File '$file' does not contain pattern '$pattern'" >> "$TEST_OUTPUT"
        return
    fi
    echo "success:File '$file' contains expected pattern" >> "$TEST_OUTPUT"
}

test_output_log () {
    local committer_name="$1"
    local committer_email="$2"
    local commit_message="$3"
    local branch="$4"
    local title="$5"
    local body="$6"
    cat << EOF > /tmp/output.log
git log -1 --pretty=%B
git checkout -b ${branch}
git config --global user.name "${committer_name}"
git config --global user.email ${committer_email}
git commit . -m "${commit_message}"
git push --no-verify --set-upstream origin ${branch}
gh pr create -B main -H ${branch} --title "${title}" --body "${body}


Signed-off-by: Mock User <mock@example.com>"
EOF
    cmp -s /tmp/output.log "$MOCK_LOG" || {
        echo "fail:Output does not match" >> "$TEST_OUTPUT"
        diff -u /tmp/output.log "$MOCK_LOG"
        return
    }
    echo "success:Output matches" >> "$TEST_OUTPUT"
}

test_nocommit_output_log () {
    local committer_name="$1"
    local committer_email="$2"
    local commit_message="$3"
    local branch="$4"
    local title="$5"
    local body="$6"
    cat << EOF > /tmp/output.log
git log -1 --pretty=%B
git checkout -b ${branch}
git push --no-verify --set-upstream origin ${branch}
gh pr create -B main -H ${branch} --title "${title}" --body "${body}


Signed-off-by: Mock User <mock@example.com>"
EOF
    cmp -s /tmp/output.log "$MOCK_LOG" || {
        echo "fail:Output does not match" >> "$TEST_OUTPUT"
        diff -u /tmp/output.log "$MOCK_LOG"
        return
    }
    echo "success:Output matches" >> "$TEST_OUTPUT"
}

test_dryrun_output_log () {
    local committer_name="$1"
    local committer_email="$2"
    local commit_message="$3"
    local branch="$4"
    local title="$5"
    local body="$6"
    cat << EOF > /tmp/output.log
git log -1 --pretty=%B
git checkout -b ${branch}
git config --global user.name "${committer_name}"
git config --global user.email ${committer_email}
git commit . -m "${commit_message}"
EOF
    cmp -s /tmp/output.log "$MOCK_LOG" || {
        echo "fail:Output does not match" >> "$TEST_OUTPUT"
        diff -u /tmp/output.log "$MOCK_LOG"
        return
    }
    echo "success:Output matches" >> "$TEST_OUTPUT"
}

trim_trailing() {
    sed -e :a -e '/[^[:space:]]/,$!d; /^[[:space:]]*$/{ $d; N; ba' -e '}'
}

setup_test () {
    {
        echo "TEST_COMMITTER_EMAIL=${TEST_COMMITTER_EMAIL}"
        echo "TEST_COMMITTER_NAME=${TEST_COMMITTER_NAME}"
        echo "TEST_BRANCH=${TEST_BRANCH}"
        echo "TEST_TITLE=${TEST_TITLE}"
        echo "TEST_COMMIT_MESSAGE<<EOF"$'\n'"$(echo "$TEST_COMMIT_MESSAGE" | trim_trailing)"$'\n'"EOF"
        echo "TEST_BODY<<EOF"$'\n'"$(echo "$TEST_BODY" | trim_trailing)"$'\n'"EOF"
    } >> "$GITHUB_ENV"
}
