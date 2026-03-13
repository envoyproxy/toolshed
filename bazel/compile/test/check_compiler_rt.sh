#!/bin/bash
# Checks that a cross-compiled binary has (or does not have) compiler-rt builtins statically linked.
#
# Required environment variables:
#   BINARY             - path to the compiled binary
#   EXPECTED_ARCH      - expected ELF architecture (e.g. AArch64, X86-64)
#   EXPECT_COMPILER_RT - "true" if libclang_rt.builtins.a should be statically linked, "false" otherwise
#   LLVM_NM            - path to llvm-nm binary
#   LLVM_READELF       - path to llvm-readelf binary
set -euo pipefail

: "${BINARY:?BINARY must be set to the path of the compiled binary}"
: "${EXPECTED_ARCH:?EXPECTED_ARCH must be set to the expected architecture (e.g. AArch64, X86-64)}"
: "${EXPECT_COMPILER_RT:?EXPECT_COMPILER_RT must be set to 'true' or 'false'}"
: "${LLVM_NM:?LLVM_NM must be set to the path of llvm-nm}"
: "${LLVM_READELF:?LLVM_READELF must be set to the path of llvm-readelf}"

# Check architecture using llvm-readelf -h
READELF_OUTPUT="$("${LLVM_READELF}" -h "${BINARY}")"
echo "llvm-readelf -h output:"
echo "${READELF_OUTPUT}"

if echo "${READELF_OUTPUT}" | grep -q "${EXPECTED_ARCH}"; then
    echo "PASS: binary is ${EXPECTED_ARCH}"
else
    echo "FAIL: expected ${EXPECTED_ARCH} in readelf output"
    exit 1
fi

# Check for __divti3 defined (T/t) symbol via llvm-nm.
# __divti3 is the 128-bit signed integer division function provided by
# compiler-rt builtins (libclang_rt.builtins.a). Its presence as a defined
# symbol proves that compiler-rt was statically linked.
NM_OUTPUT="$("${LLVM_NM}" "${BINARY}")"
echo "llvm-nm output (filtered):"
echo "${NM_OUTPUT}" | grep -i "__divti3" || echo "(no __divti3 symbols found)"

COMPILER_RT_DEFINED="false"
if grep -qE '[Tt] __divti3' <<< "${NM_OUTPUT}"; then
    COMPILER_RT_DEFINED="true"
fi

# Check for libgcc_s in dynamic NEEDED entries via llvm-readelf -d
DYNAMIC_OUTPUT="$("${LLVM_READELF}" -d "${BINARY}")"
echo "llvm-readelf -d output:"
echo "${DYNAMIC_OUTPUT}"

HAS_LIBGCC_S="false"
if echo "${DYNAMIC_OUTPUT}" | grep -q "libgcc_s"; then
    HAS_LIBGCC_S="true"
fi

if [[ "${EXPECT_COMPILER_RT}" = "true" ]]; then
    if [ "${COMPILER_RT_DEFINED}" = "true" ]; then
        echo "PASS: __divti3 is defined (statically linked from libclang_rt.builtins.a)"
    else
        echo "FAIL: expected __divti3 to be a defined (T/t) symbol, but it was not found"
        exit 1
    fi
    if [[ "${HAS_LIBGCC_S}" = "false" ]]; then
        echo "PASS: no libgcc_s in dynamic NEEDED entries"
    else
        echo "FAIL: found libgcc_s in dynamic NEEDED entries (binary is using libgcc fallback)"
        exit 1
    fi
else
    if [[ "${COMPILER_RT_DEFINED}" = "false" ]]; then
        echo "PASS: __divti3 is not a defined (T/t) symbol (compiler-rt not statically linked)"
    else
        echo "FAIL: expected __divti3 to NOT be a defined (T/t) symbol, but it was found"
        exit 1
    fi
fi
