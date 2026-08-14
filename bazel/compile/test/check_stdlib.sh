#!/bin/bash
# Checks that a binary was linked against the expected C++ standard library.
#
# libstdc++ (gcc) mangles std::string and friends into the __cxx11 inline
# namespace; libc++ (llvm) uses std::__1. The two are mutually exclusive in a
# correctly built binary, so presence of one and absence of the other is a
# reliable signal of which toolchain actually compiled the code -- as opposed
# to which one the build claims to have selected.
#
# Required environment variables:
#   BINARY          - path to the compiled binary
#   EXPECTED_STDLIB - "libstdcxx" or "libcxx"
#
# Optional environment variables:
#   NM              - path to nm (defaults to `nm` on PATH)
set -euo pipefail

: "${BINARY:?BINARY must be set to the path of the compiled binary}"
: "${EXPECTED_STDLIB:?EXPECTED_STDLIB must be set to 'libstdcxx' or 'libcxx'}"

NM="${NM:-nm}"

if ! command -v "${NM}" >/dev/null 2>&1; then
    echo "FAIL: ${NM} not found"
    exit 1
fi

# -C demangles; without it the inline namespace markers are harder to match.
NM_OUTPUT="$("${NM}" -C "${BINARY}" 2>/dev/null || true)"

if [[ -z "${NM_OUTPUT}" ]]; then
    echo "FAIL: ${NM} produced no output for ${BINARY}"
    exit 1
fi

CXX11_COUNT="$(grep -c '__cxx11' <<< "${NM_OUTPUT}" || true)"
CXXABI1_COUNT="$(grep -c 'std::__1' <<< "${NM_OUTPUT}" || true)"

echo "__cxx11 (libstdc++) symbols:  ${CXX11_COUNT}"
echo "std::__1 (libc++) symbols:    ${CXXABI1_COUNT}"

rc=0

case "${EXPECTED_STDLIB}" in
    libstdcxx)
        if [[ "${CXX11_COUNT}" -gt 0 ]]; then
            echo "PASS: found libstdc++ (__cxx11) symbols"
        else
            echo "FAIL: expected libstdc++ (__cxx11) symbols, found none"
            rc=1
        fi
        if [[ "${CXXABI1_COUNT}" -eq 0 ]]; then
            echo "PASS: no libc++ (std::__1) symbols"
        else
            echo "FAIL: found ${CXXABI1_COUNT} libc++ (std::__1) symbols in a libstdc++ build"
            echo "      this usually means toolchain resolution silently fell back to LLVM"
            rc=1
        fi
        ;;
    libcxx)
        if [[ "${CXXABI1_COUNT}" -gt 0 ]]; then
            echo "PASS: found libc++ (std::__1) symbols"
        else
            echo "FAIL: expected libc++ (std::__1) symbols, found none"
            rc=1
        fi
        if [[ "${CXX11_COUNT}" -eq 0 ]]; then
            echo "PASS: no libstdc++ (__cxx11) symbols"
        else
            echo "FAIL: found ${CXX11_COUNT} libstdc++ (__cxx11) symbols in a libc++ build"
            rc=1
        fi
        ;;
    *)
        echo "FAIL: EXPECTED_STDLIB must be 'libstdcxx' or 'libcxx', got '${EXPECTED_STDLIB}'"
        exit 1
        ;;
esac

exit "${rc}"
