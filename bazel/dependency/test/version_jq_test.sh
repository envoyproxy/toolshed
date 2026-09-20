#!/bin/bash
set -euo pipefail

if [ -n "${TEST_SRCDIR:-}" ]; then
  if [ -d "${TEST_SRCDIR}/envoy_toolshed" ]; then
    RUNFILES_DIR="${TEST_SRCDIR}/envoy_toolshed"
  else
    RUNFILES_DIR="${TEST_SRCDIR}/_main"
  fi
  JQ_DIR="${RUNFILES_DIR}/dependency"
  TEST_JQ_DIR="${RUNFILES_DIR}/dependency/test"
else
  SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  JQ_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
  TEST_JQ_DIR="${SCRIPT_DIR}"
fi

assert_compare() {
  local left="$1"
  local right="$2"
  local expected="$3"
  local actual

  actual="$(${JQ_BIN} -nr -L "${JQ_DIR}" --arg a "${left}" --arg b "${right}" -f "${TEST_JQ_DIR}/version_compare.jq")"
  [[ "${actual}" == "${expected}" ]] || {
    echo "expected ${left} ? ${right} => ${expected}, got ${actual}" >&2
    exit 1
  }
}

assert_compare 1.8.2 1.9.0 -1
assert_compare 1.9.0 1.9.0.bcr.1 -1
assert_compare 1.9.0-rc1 1.9.0 -1
assert_compare 1.0.rc1 1.0.rc2 -1
assert_compare 0.20260413.0 0.20260813.0 -1
assert_compare 2.2.0 2.2.0.envoy -1
assert_compare 2.2.0.envoy 2.2.0 1
assert_compare 35.1.bcr.envoy 35.1.bcr.10 1
assert_compare 35.1.bcr.10 35.1.bcr.2 1
assert_compare 1.9.0 1.9.0.bcr.1 -1

sorted="$(${JQ_BIN} -nr -L "${JQ_DIR}" --argjson versions '["35.1.bcr.10","35.1.bcr.2","35.1.bcr.1","1.9.0-rc1","1.9.0","1.9.0.bcr.1"]' -f "${TEST_JQ_DIR}/version_sort.jq")"
expected=$'1.9.0-rc1\n1.9.0\n1.9.0.bcr.1\n35.1.bcr.1\n35.1.bcr.2\n35.1.bcr.10'
if [[ "${sorted}" != "${expected}" ]]; then
  echo "unexpected sort order:" >&2
  printf '%s\n' "${sorted}" >&2
  exit 1
fi
