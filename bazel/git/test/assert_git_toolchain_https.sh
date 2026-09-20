#!/bin/bash
set -euo pipefail

: "${GIT:?GIT must be set}"

home_dir="${TEST_TMPDIR}/home"
mkdir -p "$home_dir"

git_cmd() {
    env -i \
        HOME="$home_dir" \
        PATH="/usr/bin:/bin" \
        "$@"
}

exec_path=$(git_cmd "$GIT" --exec-path)
bundled_cacert="$exec_path/../../share/git-core/ca-certificates.crt"
copied_cacert="${TEST_TMPDIR}/copied-ca-certificates.crt"
cp "$bundled_cacert" "$copied_cacert"

ls_remote_output=$(git_cmd "$GIT" ls-remote --exit-code https://github.com/envoyproxy/toolshed.git HEAD)
printf '%s\n' "$ls_remote_output" | grep -Eq '^[0-9a-f]{40}[[:space:]]+HEAD$'

if git_cmd GIT_SSL_CAINFO=/nonexistent "$GIT" ls-remote --exit-code https://github.com/envoyproxy/toolshed.git HEAD >/dev/null 2>&1; then
    echo "git unexpectedly succeeded with invalid GIT_SSL_CAINFO override" >&2
    exit 1
fi

ls_remote_with_override=$(git_cmd TOOLSHED_CA_BUNDLE="$copied_cacert" "$GIT" ls-remote --exit-code https://github.com/envoyproxy/toolshed.git HEAD)
printf '%s\n' "$ls_remote_with_override" | grep -Eq '^[0-9a-f]{40}[[:space:]]+HEAD$'

echo "PASS: git toolchain https checks passed"
