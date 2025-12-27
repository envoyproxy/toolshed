
test_checkout () {
    if [[ ! -d ".git" ]]; then
        echo "fail:Repository not checked out (.git directory missing)" >> $TEST_OUTPUT
        return
    fi
    echo "success:Repository checked out successfully" >> $TEST_OUTPUT
}

test_depth () {
    local min_depth="${1}"
    local max_depth="${2}"
    local commit_count=$(git rev-list --count HEAD)

    # In a PR, we need to account for:
    # - The merge commit (1)
    # - The fetch-depth from base branch
    # - Commits in the PR itself
    local pr_commit_count=0
    if [[ -n "$GITHUB_BASE_REF" ]]; then
        # We're in a PR context
        # Count commits between base and head
        git fetch origin "${GITHUB_BASE_REF}"
        pr_commit_count=$(git rev-list --count "origin/${GITHUB_BASE_REF}..HEAD" 2>/dev/null || echo 0)
        # Subtract 1 for the merge commit
        pr_commit_count=$((pr_commit_count > 0 ? pr_commit_count - 1 : 0))
    fi

    # Adjust expectations
    local adjusted_min=$((min_depth + pr_commit_count))
    local adjusted_max=$((max_depth + pr_commit_count))

    echo "Commit count: $commit_count"
    echo "PR Commit count: $pr_commit_count"
    git log
    if [[ -n "$adjusted_min" ]]; then
        if [[ $commit_count -lt "${adjusted_min}" ]]; then
            echo "fail:Expected min (fetch-depth: ${adjusted_min}), but only got $commit_count commits" >> "$TEST_OUTPUT"
        else
            echo "success:Expected min (fetch-depth: ${adjusted_min}) applied correctly, got $commit_count commits" >> "$TEST_OUTPUT"
            git log
        fi
    fi
    if [[ -n "$adjusted_max" ]]; then
        if [[ $commit_count -gt "${adjusted_max}" ]]; then
            echo "fail:Expected max (fetch-depth: ${adjusted_max}), but got $commit_count commits" >> "$TEST_OUTPUT"
        else
            echo "success:Expected max (fetch-depth: ${adjusted_max}) applied correctly, got $commit_count commits" >> "$TEST_OUTPUT"
            git log
        fi
    fi
}

test_git_config () {
    # Verify git user.name is set
    expected_name="${1}"
    expected_email="${2}"
    GIT_NAME="$(git config --global user.name)"
    if [[ "$GIT_NAME" != "${expected_name}" ]]; then
        echo "fail:Expected git user.name '${expected_name}', got '$GIT_NAME'" >> "$TEST_OUTPUT"
    else
        echo "success:Git user.name correctly set: $GIT_NAME" >> "$TEST_OUTPUT"
    fi
    GIT_EMAIL=$(git config --global user.email)
    if [[ "$GIT_EMAIL" != "${expected_email}" ]]; then
        echo "fail:Expected git user.email '${expected_email}', got '$GIT_EMAIL'" >> "$TEST_OUTPUT"
    else
        echo "success:Git user.email correctly set: $GIT_EMAIL" >> "$TEST_OUTPUT"
    fi
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
