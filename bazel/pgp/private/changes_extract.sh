#!/usr/bin/env bash
set -euo pipefail

tarball="$1"
package="$2"
prefix="$3"
out="$4"

tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

tar xf "$tarball" -C "$tmp"

prefix="${prefix#/}"
prefix="${prefix%/}"

shopt -s nullglob
matches=("$tmp"/${prefix:+"$prefix"/}"${package}_"*.changes)
shopt -u nullglob

if [[ "${#matches[@]}" -ne 1 ]]; then
    echo "expected exactly one ${package}_*.changes under ${prefix}/ in ${tarball}, got ${#matches[@]}" >&2
    exit 1
fi

cp "${matches[0]}" "$out"
