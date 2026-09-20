#!/bin/bash
set -euo pipefail

: "${TAR:?TAR must be set}"
: "${TARBALL:?TARBALL must be set}"


TAR="$(realpath "$TAR")"

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

"$TAR" -xf "$TARBALL" -C "$tmp"

pkg_dir=$(find "$tmp" -mindepth 1 -maxdepth 1 -type d -name 'git-*' -print -quit)
test -n "$pkg_dir"

git_wrapper="$pkg_dir/bin/git"
bundled_cacert="$pkg_dir/share/git-core/ca-certificates.crt"
copied_cacert="$tmp/copied-ca-certificates.crt"
home_dir="$tmp/home"

mkdir -p "$home_dir"
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

echo "PASS: git https checks passed"
