#!/bin/bash
set -euo pipefail

: "${GIT:?GIT must be set}"

home_dir="${TEST_TMPDIR}/home"
mkdir -p "$home_dir"

git_wrapper=$(realpath "$GIT")
here="$(CDPATH= cd "$(dirname "$git_wrapper")/.." && pwd)"
bundled_cacert="$here/share/git-core/ca-certificates.crt"
copied_cacert="${TEST_TMPDIR}/copied-ca-certificates.crt"
cp "$bundled_cacert" "$copied_cacert"

git_cmd() {
    env -i \
        HOME="$home_dir" \
        PATH="/usr/bin:/bin" \
        "$@"
}

ls_remote_output=$(git_cmd "$git_wrapper" ls-remote --exit-code https://github.com/envoyproxy/toolshed.git HEAD)
printf '%s\n' "$ls_remote_output" | grep -Eq '^[0-9a-f]{40}[[:space:]]+HEAD$'

if git_cmd GIT_SSL_CAINFO=/nonexistent "$git_wrapper" ls-remote --exit-code https://github.com/envoyproxy/toolshed.git HEAD >/dev/null 2>&1; then
    echo "git unexpectedly succeeded with invalid GIT_SSL_CAINFO override" >&2
    exit 1
fi

ls_remote_with_override=$(git_cmd TOOLSHED_CA_BUNDLE="$copied_cacert" "$git_wrapper" ls-remote --exit-code https://github.com/envoyproxy/toolshed.git HEAD)
printf '%s\n' "$ls_remote_with_override" | grep -Eq '^[0-9a-f]{40}[[:space:]]+HEAD$'

echo "PASS: git toolchain https checks passed"
