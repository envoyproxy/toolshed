#!/bin/bash
set -euo pipefail

: "${TARBALL:?TARBALL must be set}"
: "${READELF:?READELF must be set}"
: "${GIT_VERSION:?GIT_VERSION must be set}"
: "${GLIBC_FLOOR:?GLIBC_FLOOR must be set}"

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

tar -xf "$TARBALL" -C "$tmp"

pkg_dir=$(find "$tmp" -mindepth 1 -maxdepth 1 -type d -name 'git-*' -print -quit)
test -n "$pkg_dir"

git_bin="$pkg_dir/bin/git"
git_remote_http="$pkg_dir/libexec/git-core/git-remote-http"
git_remote_https="$pkg_dir/libexec/git-core/git-remote-https"
git_templates="$pkg_dir/share/git-core/templates"
home_dir="$tmp/home"

test -x "$git_bin"
test -x "$git_remote_http"
test -x "$git_remote_https"
test -d "$git_templates"
find "$git_templates" -type f -print -quit | grep -q .

version=$("$git_bin" --version 2>&1 || true)
test "${version%%$'\n'*}" = "git version $GIT_VERSION"

git_cmd() {
    env \
        HOME="$home_dir" \
        GIT_CONFIG_NOSYSTEM=1 \
        GIT_EXEC_PATH="$pkg_dir/libexec/git-core" \
        GIT_TEMPLATE_DIR="$git_templates" \
        "$git_bin" "$@"
}

mkdir -p "$home_dir" "$tmp/repo"
git_cmd init "$tmp/repo" >/dev/null
git_cmd -C "$tmp/repo" config user.name toolshed
git_cmd -C "$tmp/repo" config user.email toolshed@example.com
printf 'hello\n' >"$tmp/repo/README"
git_cmd -C "$tmp/repo" add README
git_cmd -C "$tmp/repo" commit -m initial >/dev/null
head_sha=$(git_cmd -C "$tmp/repo" rev-parse HEAD)
test ${#head_sha} -eq 40

if "$READELF" -d "$git_bin" | grep -Eq 'NEEDED.*(libssl|libcrypto|libcurl|libz|libexpat|libpcre2)'; then
    echo "git unexpectedly links to non-hermetic shared libraries" >&2
    exit 1
fi

python3 - "$GLIBC_FLOOR" "$git_bin" "$READELF" <<'PY'
import re
import subprocess
import sys

floor, binary, readelf = sys.argv[1:4]
output = subprocess.check_output([readelf, "-V", binary], text=True, stderr=subprocess.STDOUT)
versions = sorted({tuple(map(int, v.split("."))) for v in re.findall(r"GLIBC_(\d+(?:\.\d+)+)", output)})
floor_tuple = tuple(map(int, floor.split(".")))
too_new = [".".join(map(str, version)) for version in versions if version > floor_tuple]
if too_new:
    raise SystemExit(f"FAIL: GLIBC requirement exceeds {floor}: {', '.join(too_new)}")
print(f"PASS: max GLIBC requirement <= {floor}")
PY

echo "PASS: git manifest checks passed"
