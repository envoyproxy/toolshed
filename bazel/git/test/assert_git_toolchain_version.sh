#!/bin/bash
set -euo pipefail

: "${GIT:?GIT must be set}"
: "${GIT_VERSION:?GIT_VERSION must be set}"
: "${REPO_NAME_FILE:?REPO_NAME_FILE must be set}"

repo_name=$(tr -d '\n' <"$REPO_NAME_FILE")
home_dir="${TEST_TMPDIR}/home"
repo_dir="${TEST_TMPDIR}/repo"
mkdir -p "$home_dir" "$repo_dir"

git_cmd() {
    env -i \
        HOME="$home_dir" \
        PATH="/usr/bin:/bin" \
        "$GIT" "$@"
}

version=$(git_cmd --version)
test "$version" = "git version $GIT_VERSION"

git_cmd init "$repo_dir" >/dev/null
test -d "$repo_dir/.git"

echo "$repo_name" | grep -Eq '^[A-Za-z0-9_+.-]+$'

if [[ "${EXPECT_SOURCE_ONLY:-0}" == "1" ]]; then
    if [[ "$repo_name" == git_prebuilt_* ]]; then
        echo "expected source toolchain, got prebuilt repo $repo_name" >&2
        exit 1
    fi
fi

echo "PASS: git toolchain version/init checks passed"
