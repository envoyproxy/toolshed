#!/bin/bash
set -euo pipefail

if [ -n "${TEST_SRCDIR:-}" ]; then
  if [ -d "${TEST_SRCDIR}/envoy_toolshed" ]; then
    RUNFILES_DIR="${TEST_SRCDIR}/envoy_toolshed"
  else
    RUNFILES_DIR="${TEST_SRCDIR}/_main"
  fi
  FILTER="${RUNFILES_DIR}/dependency/module_deps_json.jq"
  LOCKFILE="${RUNFILES_DIR}/dependency/test/testdata/module/MODULE.duplicate.lock"
  JQ_DIR="${RUNFILES_DIR}/dependency"
else
  SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  FILTER="${SCRIPT_DIR}/../module_deps_json.jq"
  LOCKFILE="${SCRIPT_DIR}/testdata/module/MODULE.duplicate.lock"
  JQ_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
fi

err="$(mktemp)"
declared="$(mktemp)"
trap 'rm -f "${declared}" "${err}"' EXIT
printf 'protobuf 35.2.bcr.envoy\n' >"${declared}"
if "${JQ_BIN}" --rawfile declared "${declared}" -L "${JQ_DIR}" -f "${FILTER}" "${LOCKFILE}" >/dev/null 2>"${err}"; then
  echo "expected duplicate lockfile parse to fail" >&2
  exit 1
fi
grep -F 'Multiple source.json entries for module protobuf' "${err}" >/dev/null
