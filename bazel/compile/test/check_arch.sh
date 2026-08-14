#!/bin/bash
# Checks that a cross-compiled binary is of the expected ELF architecture.
# The BINARY, EXPECTED_ARCH, and LLVM_READELF environment variables must be set.
set -euo pipefail

: "${BINARY:?BINARY must be set to the path of the compiled binary}"
: "${EXPECTED_ARCH:?EXPECTED_ARCH must be set to the expected architecture (e.g. AArch64, X86-64)}"
: "${LLVM_READELF:?LLVM_READELF must be set to the path of llvm-readelf}"

READELF_OUTPUT="$("${LLVM_READELF}" --file-header "${BINARY}")"
echo "llvm-readelf output: ${READELF_OUTPUT}"

MACHINE="$(
    echo "${READELF_OUTPUT}" \
        | sed -n 's/^[[:space:]]*Machine:[[:space:]]*//p' \
        | head -n 1
)"

echo "machine: ${MACHINE:-<missing>}"

if [[ -n "${MACHINE}" ]] && grep -Fq "${EXPECTED_ARCH}" <<<"${MACHINE}"; then
    echo "PASS: binary is ${EXPECTED_ARCH}"
else
    echo "FAIL: expected machine ${EXPECTED_ARCH}, got: ${MACHINE:-<missing>}"
    exit 1
fi
