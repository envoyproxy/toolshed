#!/usr/bin/env bash
# Helper script to compute SHA256 checksums for libstdc++ .deb files
# used by the LIBSTDCXX_SHA256 table in build_sysroot.sh.
#
# Run this script once whenever version pins are added or updated, then
# paste the output into build_sysroot.sh replacing the "TBD" values.
#
# Requires: curl, sha256sum
#
# Usage:
#   bash compute_libstdcxx_sha256s.sh
#
# Example (update table and verify output before editing build_sysroot.sh):
#   bash compute_libstdcxx_sha256s.sh | grep '^LIBSTDCXX_SHA256'

set -e -o pipefail

# These must match the values in build_sysroot.sh
LIBSTDCXX_POOL="https://ppa.launchpadcontent.net/ubuntu-toolchain-r/test/ubuntu/pool/main/g/gcc-13"

declare -A VERSIONS
VERSIONS["bionic,13"]="13.1.0-8ubuntu1~18.04"   # last bionic upload 2023-07-13
VERSIONS["focal,13"]="13.3.0-6ubuntu2~20.04"    # latest focal upload 2026-05-01

COMBOS=(
    "bionic,13,amd64"
    "focal,13,amd64"
    "focal,13,arm64"
)

tmp=$(mktemp -d)
# shellcheck disable=SC2064
trap "rm -rf '${tmp}'" EXIT

echo "# Computing SHA256 checksums for LIBSTDCXX_SHA256 table in build_sysroot.sh"
echo "# Pool: ${LIBSTDCXX_POOL}"
echo ""

for combo in "${COMBOS[@]}"; do
    IFS=',' read -r toolchain stdcc arch <<< "$combo"
    ver_key="${toolchain},${stdcc}"
    ver="${VERSIONS[$ver_key]:-}"
    if [[ -z "$ver" ]]; then
        echo "ERROR: No version entry for ${toolchain},${stdcc}" >&2
        exit 1
    fi

    echo "# (${toolchain}, gcc-${stdcc}, ${arch}) — version ${ver}"

    deb_base="gcc-${stdcc}-base_${ver}_${arch}.deb"
    deb_libstdcpp6="libstdc++6_${ver}_${arch}.deb"
    deb_dev="libstdc++-${stdcc}-dev_${ver}_${arch}.deb"

    for entry in "${deb_base}|base" "${deb_libstdcpp6}|libstdcpp6" "${deb_dev}|dev"; do
        deb="${entry%%|*}"
        pkgtype="${entry##*|}"
        url="${LIBSTDCXX_POOL}/${deb}"
        dest="${tmp}/${deb}"

        echo "  Downloading: ${deb}..." >&2
        curl -fsSL -o "$dest" "$url"
        sha256=$(sha256sum "$dest" | awk '{print $1}')
        echo "LIBSTDCXX_SHA256[\"${toolchain},${stdcc},${arch},${pkgtype}\"]=\"${sha256}\""
        rm -f "$dest"
    done
    echo ""
done

echo "# Done. Paste the LIBSTDCXX_SHA256[...] lines into build_sysroot.sh"
echo "# replacing the corresponding TBD values."
