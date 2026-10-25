#!/bin/bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
export BINARY=fixture.a
export NM="${PWD}/glibc_tool_fixture.sh"
export READELF="${NM}"
export CHECK_STATIC_RUNTIME=true

assert_check() {
    local expected="$1"
    shift
    local output status=0
    output="$(env "$@" bash ./check_glibc.sh 2>&1)" || status=$?
    if [[ "${expected}" == "pass" && "${status}" -ne 0 ]] ||
        [[ "${expected}" == "fail" && "${status}" -eq 0 ]]; then
        printf 'FAIL: expected %s for %s\n%s\n' "${expected}" "$*" "${output}"
        exit 1
    fi
    echo "PASS: expected ${expected} for $*"
}

assert_check pass
assert_check pass FIXTURE_UNDEFINED='U memcpy@GLIBC_2.9'
assert_check pass FIXTURE_UNDEFINED='U memcpy@GLIBC_2.31.0'
assert_check pass FIXTURE_UNDEFINED='U memcpy@GLIBC_2.3.4'
assert_check pass FIXTURE_UNDEFINED='U ordinary_symbol'
assert_check pass FIXTURE_UNDEFINED='U prefixed__isoc23_strtol'
assert_check pass FIXTURE_UNDEFINED='U prefixed__libc_single_threaded'
assert_check pass FIXTURE_VERSIONS='Name: GLIBCXX_3.4.32 Name: GLIBC_2.31'
assert_check fail FIXTURE_UNDEFINED='U memcpy@GLIBC_2.32'
assert_check fail FIXTURE_UNDEFINED='U memcpy@GLIBC_2.100'
assert_check fail FIXTURE_UNDEFINED='U memcpy@GLIBC_2.31.1'
assert_check fail FIXTURE_UNDEFINED='U memcpy@GLIBC_3.0'
assert_check fail FIXTURE_VERSIONS='Name: GLIBC_2.9 Name: GLIBC_2.34'
assert_check fail FIXTURE_UNDEFINED='U __isoc23_strtol'
assert_check fail FIXTURE_UNDEFINED='U __isoc23_sscanf@GLIBC_2.38'
assert_check fail FIXTURE_UNDEFINED='U __libc_single_threaded'
assert_check fail FIXTURE_UNDEFINED='w __libc_single_threaded@GLIBC_2.32'
assert_check fail FIXTURE_UNDEFINED='U __libc_single_threaded@@GLIBC_2.32'
assert_check fail FIXTURE_LARGE=true FIXTURE_UNDEFINED='U __isoc23_strtoul'
assert_check pass FIXTURE_LARGE=true
assert_check fail FIXTURE_DYNAMIC='0x00000001 (NEEDED) Shared library: [libstdc++.so.6]'
assert_check fail FIXTURE_DYNAMIC='0x00000001 (NEEDED) Shared library: [libgcc_s.so.1]'
assert_check pass FIXTURE_DYNAMIC='0x00000001 (NEEDED) Shared library: [libc.so.6]'
assert_check fail FIXTURE_NM_FAIL=true
assert_check fail FIXTURE_READELF_FAIL=true
