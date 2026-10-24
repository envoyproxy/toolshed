#!/bin/bash
set -euo pipefail

: "${LIBUNWIND:?LIBUNWIND must be set to the built shared library}"
: "${LLVM_READELF:?LLVM_READELF must be set to the path of llvm-readelf}"

MAX_GLIBC_VERSION=2.31

DYNAMIC_OUTPUT="$("${LLVM_READELF}" -d "${LIBUNWIND}")"
echo "${DYNAMIC_OUTPUT}"
if ! grep -Eq '\(SONAME\).*\[libunwind\.so\.1\]' <<< "${DYNAMIC_OUTPUT}"; then
    echo "FAIL: expected SONAME libunwind.so.1"
    exit 1
fi
if grep -Eq '\(NEEDED\).*libgcc_s' <<< "${DYNAMIC_OUTPUT}"; then
    echo "FAIL: libunwind must not depend on libgcc_s"
    exit 1
fi

VERSION_OUTPUT="$("${LLVM_READELF}" --dyn-syms --version-info "${LIBUNWIND}")"
echo "${VERSION_OUTPUT}"
awk -v max="${MAX_GLIBC_VERSION}" '
    BEGIN { split(max, limit, ".") }
    {
        while (match($0, /GLIBC_[0-9]+\.[0-9]+(\.[0-9]+)?/)) {
            version = substr($0, RSTART + 6, RLENGTH - 6)
            split(version, parts, ".")
            if (parts[1] > limit[1] ||
                (parts[1] == limit[1] && parts[2] > limit[2]) ||
                (parts[1] == limit[1] && parts[2] == limit[2] && parts[3] + 0 > 0)) {
                print "FAIL: GLIBC_" version " exceeds sysroot baseline " max
                failed = 1
            }
            $0 = substr($0, RSTART + RLENGTH)
        }
    }
    END { exit failed }
' <<< "${VERSION_OUTPUT}"

echo "PASS: shared libunwind has the expected SONAME, no libgcc_s, and GLIBC <= ${MAX_GLIBC_VERSION}"
