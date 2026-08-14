#!/bin/bash
# Verifies the built wee8 artifacts match what their filenames claim.
#
# Artifact names encode both the target architecture and the C++ standard
# library, e.g.
#
#   v8-wee8-14.6.202.10-linux-x86_64-libstdcxx.tar.xz
#   v8-wee8-14.6.202.10-linux-aarch64.tar.xz          (libcxx, implicit)
#
# Both are claims made by the build, and both have silently been wrong:
# toolchain resolution can fall back to LLVM when a gcc toolchain fails to
# resolve, and a cross-compiling toolchain that shells out to a native
# compiler produces host-arch objects under a target-arch name. Neither
# shows up as a build failure, and neither is obvious from file size.
#
# This checks the actual ELF contents of libwee8.a against the name.
#
# Usage:
#   .github/verify/artifacts/wee8.sh <artifact-dir>
#
# Sibling artifacts (libcxx/msan/tsan/sysroot) should get their own scripts
# alongside this one.
set -euo pipefail

ARTIFACT_DIR="${1:?usage: wee8.sh <artifact-dir>}"
CHECK_STDLIB="$(dirname "$0")/../../../bazel/compile/test/check_stdlib.sh"

# Keep in sync with WEE8_VARIANTS in bazel/v8/package/BUILD. aarch64+libstdcxx
# is deliberately absent: the gcc toolchain invokes /usr/bin/gcc directly and
# has no cross-compiler, so that combination cannot be built.
EXPECTED_COUNT=3

if [[ ! -d "${ARTIFACT_DIR}" ]]; then
    echo "FAIL: artifact dir '${ARTIFACT_DIR}' does not exist"
    exit 1
fi

shopt -s nullglob globstar

WORKDIR="$(mktemp -d)"
trap 'rm -rf "${WORKDIR}"' EXIT

found=0
rc=0

for tarball in "${ARTIFACT_DIR}"/**/v8-wee8-*.tar.xz; do
    found=$((found + 1))
    name="$(basename "${tarball}")"

    case "${name}" in
        *-libstdcxx.tar.xz) expected_stdlib="libstdcxx" ;;
        *.tar.xz)           expected_stdlib="libcxx" ;;
    esac

    case "${name}" in
        *-linux-x86_64*)  expected_arch="Advanced Micro Devices X86-64" ;;
        *-linux-aarch64*) expected_arch="AArch64" ;;
        *)
            echo "FAIL: cannot determine arch from '${name}'"
            rc=1
            continue
            ;;
    esac

    echo "=============================================================="
    echo "${name}"
    echo "  expect arch:   ${expected_arch}"
    echo "  expect stdlib: ${expected_stdlib}"
    echo "=============================================================="

    lib="${WORKDIR}/${name}.a"
    if ! tar -xOf "${tarball}" lib/libwee8.a > "${lib}"; then
        echo "FAIL: could not extract lib/libwee8.a from ${name}"
        rc=1
        continue
    fi

    # readelf cannot read an archive directly; unpack one member and read that.
    objdir="${WORKDIR}/$(basename "${lib}").objs"
    mkdir -p "${objdir}"
    (cd "${objdir}" && ar x "${lib}")
    obj="$(find "${objdir}" -name '*.o' -print -quit)"

    if [[ -z "${obj}" ]]; then
        echo "FAIL: no object files in libwee8.a from ${name}"
        rc=1
        continue
    fi

    machine="$(readelf -h "${obj}" | sed -n 's/^ *Machine: *//p')"
    echo "actual machine: ${machine}"

    if [[ "${machine}" == "${expected_arch}" ]]; then
        echo "PASS: ${name} is ${expected_arch}"
    else
        echo "FAIL: ${name} claims ${expected_arch} but objects are ${machine}"
        rc=1
    fi

    if ! BINARY="${lib}" EXPECTED_STDLIB="${expected_stdlib}" bash "${CHECK_STDLIB}"; then
        rc=1
    fi

    rm -rf "${objdir}" "${lib}"
done

echo "=============================================================="

# Without this a glob that matches nothing would pass vacuously - the same
# class of silent success this script exists to catch.
if [[ "${found}" -ne "${EXPECTED_COUNT}" ]]; then
    echo "FAIL: expected ${EXPECTED_COUNT} wee8 artifacts, found ${found}"
    exit 1
fi

if [[ "${rc}" -ne 0 ]]; then
    echo "FAIL: one or more wee8 artifacts did not match their name"
    exit 1
fi

echo "PASS: all ${found} wee8 artifacts match their names"
