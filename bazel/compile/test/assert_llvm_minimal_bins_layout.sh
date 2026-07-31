#!/bin/bash
set -euo pipefail

: "${TARBALL:?TARBALL must be set}"
: "${ROOT_DIR:?ROOT_DIR must be set}"
: "${CLANG_REAL:?CLANG_REAL must be set}"

list_file="$(mktemp)"
trap 'rm -f "$list_file"; rm -rf "${tmpdir:-}"' EXIT

tar --zstd -tvf "$TARBALL" > "$list_file"

require_link() {
  local path="$1"
  local target="$2"
  if ! grep -Eq "^l.* ${ROOT_DIR}/${path} -> ${target}$" "$list_file"; then
    echo "FAIL: missing symlink ${path} -> ${target}" >&2
    exit 1
  fi
}

require_true() {
  local message="$1"
  shift
  if ! "$@"; then
    echo "FAIL: ${message}" >&2
    exit 1
  fi
}

require_link "bin/clang" "${CLANG_REAL}"
require_link "bin/clang\+\+" "${CLANG_REAL}"
require_link "bin/clang-cpp" "${CLANG_REAL}"
require_link "bin/ld.lld" "lld"
require_link "bin/ld64.lld" "lld"
require_link "bin/wasm-ld" "lld"

tmpdir="$(mktemp -d)"
tar --zstd -xf "$TARBALL" -C "$tmpdir" \
  "${ROOT_DIR}/bin/clang" \
  "${ROOT_DIR}/bin/${CLANG_REAL}" \
  "${ROOT_DIR}/bin/lld" \
  "${ROOT_DIR}/bin/ld.lld"

BIN_DIR="$tmpdir/$ROOT_DIR/bin"

require_true "bin/clang is not symlink to ${CLANG_REAL}" test -L "$BIN_DIR/clang"
require_true "bin/clang symlink target is not ${CLANG_REAL}" test "$(readlink "$BIN_DIR/clang")" = "${CLANG_REAL}"
require_true "bin/ld.lld is not symlink to lld" test -L "$BIN_DIR/ld.lld"
require_true "bin/ld.lld symlink target is not lld" test "$(readlink "$BIN_DIR/ld.lld")" = "lld"
require_true "bin/${CLANG_REAL} must be a real file" test ! -L "$BIN_DIR/${CLANG_REAL}"
require_true "bin/lld must be a real file" test ! -L "$BIN_DIR/lld"

require_true "bin/${CLANG_REAL} is not stripped" sh -c "file \"$BIN_DIR/${CLANG_REAL}\" | grep -q stripped"
require_true "bin/lld is not stripped" sh -c "file \"$BIN_DIR/lld\" | grep -q stripped"

echo "PASS: llvm minimal bin symlink + stripped checks passed"
