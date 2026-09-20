#!/bin/bash
set -euo pipefail

: "${TAR:?TAR must be set}"
: "${TARBALL:?TARBALL must be set}"
: "${READELF:?READELF must be set}"
: "${GIT_VERSION:?GIT_VERSION must be set}"
: "${GLIBC_FLOOR:?GLIBC_FLOOR must be set}"


TAR="$(realpath "$TAR")"

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

list_file="$tmp/tar.list"
"$TAR" -tvf "$TARBALL" >"$list_file"
"$TAR" -xf "$TARBALL" -C "$tmp"

pkg_dir=$(find "$tmp" -mindepth 1 -maxdepth 1 -type d -name 'git-*' -print -quit)
test -n "$pkg_dir"

git_wrapper="$pkg_dir/bin/git"
git_bin="$pkg_dir/libexec/git-core/git"
git_remote_http="$pkg_dir/libexec/git-core/git-remote-http"
git_remote_https="$pkg_dir/libexec/git-core/git-remote-https"
git_templates="$pkg_dir/share/git-core/templates"
git_cacert="$pkg_dir/share/git-core/ca-certificates.crt"
home_dir="$tmp/home"
repo_dir="$tmp/repo"

for path in \
    "$pkg_dir/BUILD.bazel" \
    "$git_wrapper" \
    "$git_bin" \
    "$git_remote_http" \
    "$git_remote_https" \
    "$git_cacert" \
    "$git_templates"
do
    test -e "$path"
done

grep -Eq -- '^-rw-r--r-- .* git-[^/]+/BUILD\.bazel$' "$list_file"
grep -Eq -- '^-rwxr-xr-x .* git-[^/]+/bin/git$' "$list_file"
grep -Eq -- '^-rwxr-xr-x .* git-[^/]+/libexec/git-core/git$' "$list_file"
grep -Eq -- '^-rwxr-xr-x .* git-[^/]+/libexec/git-core/git-remote-http$' "$list_file"
grep -Eq -- '^l[rwx-]{9} .* git-[^/]+/libexec/git-core/git-remote-https -> git-remote-http$' "$list_file"
grep -Eq -- '^-rw-r--r-- .* git-[^/]+/share/git-core/ca-certificates\.crt$' "$list_file"
grep -Eq -- '^-rw-r--r-- .* git-[^/]+/share/git-core/templates/description$' "$list_file"
grep -Eq -- '^-rw-r--r-- .* git-[^/]+/share/git-core/templates/info/exclude$' "$list_file"
grep -Eq -- '^-rwxr-xr-x .* git-[^/]+/share/git-core/templates/hooks/.+\.sample$' "$list_file"

test "$(head -n 1 "$git_wrapper")" = "#!/bin/sh"
test -x "$git_wrapper"
test -x "$git_bin"
test -x "$git_remote_http"
test "$(stat -c '%a' "$pkg_dir/BUILD.bazel")" = "644"
test "$(stat -c '%a' "$git_wrapper")" = "755"
test "$(stat -c '%a' "$git_bin")" = "755"
test "$(stat -c '%a' "$git_remote_http")" = "755"
test -L "$git_remote_https"
test "$(readlink "$git_remote_https")" = "git-remote-http"
test "$(stat -c '%a' "$git_cacert")" = "644"
test "$(stat -c '%a' "$git_templates/description")" = "644"
test "$(stat -c '%a' "$git_templates/info/exclude")" = "644"
find "$git_templates/hooks" -type f -name '*.sample' | grep -q .
find "$git_templates/hooks" -type f -name '*.sample' -exec stat -c '%a' {} + | awk '$1 != 755 { exit 1 }'
test -d "$git_templates"
find "$git_templates" -type f -print -quit | grep -q .
find "$pkg_dir/share" \( -name Makefile -o -name meson.build -o -name .gitignore \) -print -quit | grep -q . && exit 1

cert_count=$(grep -c 'BEGIN CERTIFICATE' "$git_cacert")
test "$cert_count" -ge 100

version=$("$git_wrapper" --version 2>&1 || true)
test "${version%%$'\n'*}" = "git version $GIT_VERSION"

git_cmd() {
    env -i \
        HOME="$home_dir" \
        PATH="/usr/bin:/bin" \
        "$git_wrapper" "$@"
}

mkdir -p "$home_dir" "$repo_dir"

exec_path=$(git_cmd --exec-path)
test "$exec_path" = "$pkg_dir/libexec/git-core"

git_cmd init "$repo_dir" >/dev/null
test "$(stat -c '%a' "$repo_dir/.git/description")" = "644"
test -f "$repo_dir/.git/hooks/applypatch-msg.sample"
git_cmd -C "$repo_dir" config user.name toolshed
git_cmd -C "$repo_dir" config user.email toolshed@example.com
printf 'hello\n' >"$repo_dir/README"
git_cmd -C "$repo_dir" add README
git_cmd -C "$repo_dir" commit -m initial >/dev/null
head_sha=$(git_cmd -C "$repo_dir" rev-parse HEAD)
printf '%s\n' "$head_sha" | grep -Eq '^[0-9a-f]{40}$'

check_needed() {
    binary=$1
    unexpected=$("$READELF" -d "$binary" | awk '/NEEDED/ { gsub(/\[|\]/, "", $NF); print $NF }' | grep -Ev '^(libc\.so\.6|libm\.so\.6|libpthread\.so\.0|libdl\.so\.2|librt\.so\.1|ld-linux[^[:space:]]*\.so(\.[0-9]+)*|libgcc_s\.so\.1)$' || true)
    if [ -n "$unexpected" ]; then
        echo "unexpected shared libraries for $binary:" >&2
        printf '%s\n' "$unexpected" >&2
        exit 1
    fi
}

check_glibc_floor() {
    binary=$1
    max_version=$("$READELF" -V "$binary" | awk '
        function version_gt(a, b,    ai, bi, an, bn, i, av, bv) {
            an = split(a, ai, ".")
            bn = split(b, bi, ".")
            for (i = 1; i <= an || i <= bn; i++) {
                av = (i in ai) ? ai[i] + 0 : 0
                bv = (i in bi) ? bi[i] + 0 : 0
                if (av > bv) {
                    return 1
                }
                if (av < bv) {
                    return 0
                }
            }
            return 0
        }
        {
            while (match($0, /GLIBC_[0-9]+(\.[0-9]+)+/)) {
                version = substr($0, RSTART + 6, RLENGTH - 6)
                if (max == "" || version_gt(version, max)) {
                    max = version
                }
                $0 = substr($0, RSTART + RLENGTH)
            }
        }
        END {
            if (max != "") {
                print max
            }
        }
    ')
    if [ -n "$max_version" ] && awk -v max="$max_version" -v floor="$GLIBC_FLOOR" '
        function version_gt(a, b,    ai, bi, an, bn, i, av, bv) {
            an = split(a, ai, ".")
            bn = split(b, bi, ".")
            for (i = 1; i <= an || i <= bn; i++) {
                av = (i in ai) ? ai[i] + 0 : 0
                bv = (i in bi) ? bi[i] + 0 : 0
                if (av > bv) {
                    return 1
                }
                if (av < bv) {
                    return 0
                }
            }
            return 0
        }
        BEGIN { exit version_gt(max, floor) ? 0 : 1 }
    '; then
        echo "FAIL: GLIBC requirement for $binary exceeds $GLIBC_FLOOR: $max_version" >&2
        exit 1
    fi
}

check_needed "$git_bin"
check_needed "$git_remote_http"
check_glibc_floor "$git_bin"
check_glibc_floor "$git_remote_http"

echo "PASS: git manifest checks passed"
