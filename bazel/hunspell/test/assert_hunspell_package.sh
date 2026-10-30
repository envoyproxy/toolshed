#!/bin/bash
# Checks a published hunspell tarball: layout, modes, stripping, ELF arch, runtime deps and the
# glibc floor. Where the tarball matches the host arch, also runs the pipe check against the
# extracted binary and dictionary.
set -euo pipefail

: "${TAR:?TAR must be set}"
: "${TARBALL:?TARBALL must be set}"
: "${READELF:?READELF must be set}"
: "${PIPE_CHECK:?PIPE_CHECK must be set}"
: "${GLIBC_FLOOR:?GLIBC_FLOOR must be set}"
: "${HUNSPELL_VERSION:?HUNSPELL_VERSION must be set}"
: "${ARCH:?ARCH must be set}"

TAR="$(realpath "$TAR")"
READELF="$(realpath "$READELF")"
PIPE_CHECK="$(realpath "$PIPE_CHECK")"

fail() {
    echo "FAIL: $1" >&2
    exit 1
}

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

list_file="$tmp/tar.list"
"$TAR" -tvf "$TARBALL" >"$list_file"
"$TAR" -xf "$TARBALL" -C "$tmp"

prefix="hunspell-${HUNSPELL_VERSION}-linux-${ARCH}"
pkg_dir="$tmp/$prefix"
test -d "$pkg_dir" || fail "missing top-level $prefix/"

expect_entry() {
    local mode=$1 path=$2
    grep -Eq -- "^${mode} .* (\./)?${prefix}/${path}\$" "$list_file" \
        || fail "expected ${mode} ${prefix}/${path}"
}

expect_entry '-rw-r--r--' 'BUILD\.bazel'
expect_entry '-rwxr-xr-x' 'bin/hunspell'
expect_entry '-rw-r--r--' 'share/hunspell/en_US\.aff'
expect_entry '-rw-r--r--' 'share/hunspell/en_US\.dic'
for license in \
    dictionary-en/license \
    hunspell/COPYING \
    hunspell/COPYING.LESSER \
    hunspell/COPYING.MPL
do
    expect_entry '-rw-r--r--' "share/doc/${license//./\\.}"
done

hunspell="$pkg_dir/bin/hunspell"

case "$ARCH" in
    x86_64) machine="X86-64" ;;
    aarch64) machine="AArch64" ;;
    *) fail "unknown ARCH: $ARCH" ;;
esac
# Capture readelf output before matching: `grep -q` exits on the first match, and under
# `pipefail` the resulting SIGPIPE to readelf would fail the pipeline.
header=$("$READELF" -h "$hunspell")
[[ "$header" =~ Machine:[^$'\n']*"${machine}" ]] || fail "bin/hunspell is not ${machine}"

sections=$("$READELF" -S "$hunspell")
[[ "$sections" != *".symtab"* ]] || fail "bin/hunspell is not stripped"

# Only glibc and libgcc_s at runtime: the C++ runtime is linked statically.
unexpected=$("$READELF" -d "$hunspell" \
    | awk '/NEEDED/ { gsub(/\[|\]/, "", $NF); print $NF }' \
    | grep -Ev '^(libc\.so\.6|libm\.so\.6|libpthread\.so\.0|libdl\.so\.2|librt\.so\.1|ld-linux[^[:space:]]*\.so(\.[0-9]+)*|libgcc_s\.so\.1)$' || true)
[[ -z "$unexpected" ]] || fail "unexpected shared libraries: $unexpected"

max_glibc=$("$READELF" -V "$hunspell" | grep -Eo 'GLIBC_[0-9]+(\.[0-9]+)+' | cut -d_ -f2 | sort -uV | tail -n 1)
if [[ -n "$max_glibc" ]]; then
    highest=$(printf '%s\n%s\n' "$max_glibc" "$GLIBC_FLOOR" | sort -V | tail -n 1)
    [[ "$highest" == "$GLIBC_FLOOR" ]] || fail "requires GLIBC_${max_glibc}, above the ${GLIBC_FLOOR} floor"
fi

if [[ "$(uname -m)" == "$ARCH" ]]; then
    "$PIPE_CHECK" "$hunspell" "$pkg_dir/share/hunspell/en_US"
else
    echo "Skipping the pipe check: ${ARCH} tarball on a $(uname -m) host"
fi

echo "PASS: ${prefix} package checks passed"
