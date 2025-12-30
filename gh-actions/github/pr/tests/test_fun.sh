#!/usr/bin/env bash


test_output_log () {
    local committer_name="$1"
    local committer_email="$2"
    local commit_message="$3"
    local branch="$4"
    local title="$5"
    local body="$6"
    cat << EOF > /tmp/output.log
git checkout -b ${branch}
git config --global user.name "${committer_name}"
git config --global user.email ${committer_email}
git commit . -m "${commit_message}" --signoff
git log -1 --pretty=%B
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

test_noconfig_output_log () {
    local committer_name="$1"
    local committer_email="$2"
    local commit_message="$3"
    local branch="$4"
    local title="$5"
    local body="$6"
    cat << EOF > /tmp/output.log
git checkout -b ${branch}
git commit . -m "${commit_message}" --signoff
git log -1 --pretty=%B
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
git checkout -b ${branch}
git log -1 --pretty=%B
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
git checkout -b ${branch}
git config --global user.name "${committer_name}"
git config --global user.email ${committer_email}
git commit . -m "${commit_message}" --signoff
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
