#!/bin/bash
set -euo pipefail

: "${LIBUNWIND:?LIBUNWIND must be set to the built shared library}"
: "${LLVM_READELF:?LLVM_READELF must be set to the path of llvm-readelf}"

# Highest glibc symbol version the library may require. Must not exceed the
# glibc shipped in the toolshed sysroot (see //sysroot), otherwise the .so
# cannot be linked against that sysroot (--no-allow-shlib-undefined).
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
    BEGIN {
        split(max, limit, ".")
        lmaj = limit[1] + 0
        lmin = limit[2] + 0
    }
    {
        while (match($0, /GLIBC_[0-9]+\.[0-9]+(\.[0-9]+)?/)) {
            version = substr($0, RSTART + 6, RLENGTH - 6)
            split(version, parts, ".")
            # split() yields strings; force numeric comparison so that e.g.
            # GLIBC_2.4 ("4" > "31" lexically) is not rejected.
            maj = parts[1] + 0
            min = parts[2] + 0
            pat = parts[3] + 0
            if (maj > lmaj ||
                (maj == lmaj && min > lmin) ||
                (maj == lmaj && min == lmin && pat > 0)) {
                print "FAIL: GLIBC_" version " exceeds sysroot baseline " max
                failed = 1
            }
            $0 = substr($0, RSTART + RLENGTH)
        }
    }
    END { exit failed }
' <<< "${VERSION_OUTPUT}"

echo "PASS: shared libunwind has the expected SONAME, no libgcc_s, and GLIBC <= ${MAX_GLIBC_VERSION}"
