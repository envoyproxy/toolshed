#!/bin/bash
# The resolved git must be the test-only host toolchain (a symlink to the host's git) and
# must work as git: version, init, and ls-files in the new repo.
set -euo pipefail

: "${GIT:?GIT must be set}"
: "${REPO_NAME_FILE:?REPO_NAME_FILE must be set}"

# The marker carries the canonical repo name (eg `+git_host_test+envoy_toolshed_git_host_test`).
repo_name=$(tr -d '\n' <"$REPO_NAME_FILE")
[[ "$repo_name" == *envoy_toolshed_git_host_test ]] || {
    echo "expected the host test toolchain, got repo $repo_name" >&2
    exit 1
}

home_dir="${TEST_TMPDIR}/home"
repo_dir="${TEST_TMPDIR}/repo"
mkdir -p "$home_dir" "$repo_dir"

git_cmd() {
    env -i HOME="$home_dir" PATH="/usr/bin:/bin" "$GIT" "$@"
}

git_cmd --version | grep -q '^git version '
git_cmd init -q "$repo_dir"
test -d "$repo_dir/.git"
touch "$repo_dir/file"
git_cmd -C "$repo_dir" add file
test "$(git_cmd -C "$repo_dir" ls-files)" = "file"

echo "PASS: host git toolchain works"
