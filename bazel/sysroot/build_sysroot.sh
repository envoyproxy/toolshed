#!/usr/bin/env bash

set -euo pipefail

# Script to build a sysroot using debootstrap
# This script needs to be run with appropriate permissions (usually requires sudo)

# Parse arguments
ARCH=""
GLIBC_VERSION=""
DEBIAN_VERSION=""
PPA_TOOLCHAIN=""
STDCC_VERSION=""
VARIANT=""
OUTPUT_FILE=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --arch)
            ARCH="$2"
            shift 2
            ;;
        --glibc-version)
            GLIBC_VERSION="$2"
            shift 2
            ;;
        --debian-version)
            DEBIAN_VERSION="$2"
            shift 2
            ;;
        --ppa-toolchain)
            PPA_TOOLCHAIN="$2"
            shift 2
            ;;
        --stdcc-version)
            STDCC_VERSION="$2"
            shift 2
            ;;
        --variant)
            VARIANT="$2"
            shift 2
            ;;
        --output)
            OUTPUT_FILE="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Validate required arguments
if [[ -z "$ARCH" || -z "$GLIBC_VERSION" || -z "$DEBIAN_VERSION" || -z "$VARIANT" || -z "$OUTPUT_FILE" ]]; then
    echo "Usage: $0 --arch <arch> --glibc-version <version> --debian-version <version> --variant <base|libstdcxx> --output <file> [--ppa-toolchain <toolchain>] [--stdcc-version <version>]"
    exit 1
fi

if [[ "$VARIANT" == "libstdcxx" && (-z "$PPA_TOOLCHAIN" || -z "$STDCC_VERSION") ]]; then
    echo "Error: libstdcxx variant requires --ppa-toolchain and --stdcc-version"
    exit 1
fi

# Check if debootstrap is available
if ! command -v debootstrap &> /dev/null; then
    echo "Error: debootstrap is not installed. Please install it with:"
    echo "  sudo apt-get install debootstrap"
    exit 1
fi

# Temporary directory for sysroot
SYSROOT_DIR="sysroot-${ARCH}"

echo "Building sysroot: arch=${ARCH}, glibc=${GLIBC_VERSION}, debian=${DEBIAN_VERSION}, variant=${VARIANT}"

# Use archive.debian.org for archived releases (buster), deb.debian.org for current releases
if [[ "$DEBIAN_VERSION" == "buster" ]]; then
    DEBIAN_MIRROR="http://archive.debian.org/debian/"
    # buster uses libgcc1 (old package name)
    LIBGCC_PACKAGE="libgcc1"
else
    DEBIAN_MIRROR="http://deb.debian.org/debian/"
    # bullseye and newer use libgcc-s1
    LIBGCC_PACKAGE="libgcc-s1"
fi

# Build sysroot
echo "Running debootstrap..."
sudo debootstrap \
    --arch="${ARCH}" \
    --variant=minbase \
    "${DEBIAN_VERSION}" \
    "${SYSROOT_DIR}" \
    "${DEBIAN_MIRROR}"

# Add backports for kernel headers
echo "deb [check-valid-until=no] http://archive.debian.org/debian ${DEBIAN_VERSION}-backports main" \
    | sudo tee "${SYSROOT_DIR}/etc/apt/sources.list.d/backports.list"

# Update and install packages
echo "Installing packages..."
sudo chroot "${SYSROOT_DIR}" apt-get -qq update
sudo chroot "${SYSROOT_DIR}" apt-get -qq install --no-install-recommends -y \
    libc6 libc6-dev "${LIBGCC_PACKAGE}" libxml2-dev
sudo chroot "${SYSROOT_DIR}" apt-get -qq install --no-install-recommends -y \
    -t "${DEBIAN_VERSION}-backports" linux-libc-dev

# Install libstdc++ if requested
if [[ "$VARIANT" == "libstdcxx" ]]; then
    echo "Installing libstdc++${STDCC_VERSION}..."
    echo "deb http://ppa.launchpad.net/ubuntu-toolchain-r/test/ubuntu ${PPA_TOOLCHAIN} main" \
        | sudo tee "${SYSROOT_DIR}/etc/apt/sources.list.d/toolchain.list"
    sudo apt-key --keyring "${SYSROOT_DIR}/etc/apt/trusted.gpg" adv \
        --keyserver keyserver.ubuntu.com --recv-keys 1E9377A2BA9EF27F
    sudo chroot "${SYSROOT_DIR}" apt-get -qq update
    sudo chroot "${SYSROOT_DIR}" apt-get -qq install -y "libstdc++-${STDCC_VERSION}-dev"
fi

# Cleanup
echo "Cleaning up sysroot..."
sudo chroot "${SYSROOT_DIR}" apt-get clean
sudo rm -rf "${SYSROOT_DIR}/boot"
sudo rm -rf "${SYSROOT_DIR}/bin"
sudo rm -rf "${SYSROOT_DIR}/dev"
sudo rm -rf "${SYSROOT_DIR}/etc/alternatives"
sudo rm -rf "${SYSROOT_DIR}/etc/rmt"
sudo rm -rf "${SYSROOT_DIR}/etc/systemd"
sudo rm -rf "${SYSROOT_DIR}/etc/localtime"
sudo rm -rf "${SYSROOT_DIR}/home"
sudo rm -rf "${SYSROOT_DIR}/media"
sudo rm -rf "${SYSROOT_DIR}/opt"
sudo rm -rf "${SYSROOT_DIR}/proc"
sudo rm -rf "${SYSROOT_DIR}/root"
sudo rm -rf "${SYSROOT_DIR}/run"
sudo rm -rf "${SYSROOT_DIR}/sbin"
sudo rm -rf "${SYSROOT_DIR}/srv"
sudo rm -rf "${SYSROOT_DIR}/sys"
sudo rm -rf "${SYSROOT_DIR}/tmp"
sudo rm -rf "${SYSROOT_DIR}/usr/bin/awk"
sudo rm -rf "${SYSROOT_DIR}/usr/bin/nawk"
sudo rm -rf "${SYSROOT_DIR}/usr/bin/pager"
sudo rm -rf "${SYSROOT_DIR}/usr/bin/pidof"
sudo rm -rf "${SYSROOT_DIR}/usr/sbin"
sudo rm -rf "${SYSROOT_DIR}/usr/share/doc"
sudo rm -rf "${SYSROOT_DIR}/usr/share/info"
sudo rm -rf "${SYSROOT_DIR}/usr/share/lintian"
sudo rm -rf "${SYSROOT_DIR}/usr/share/man"
sudo rm -rf "${SYSROOT_DIR}/usr/share/zoneinfo"
sudo rm -rf "${SYSROOT_DIR}/var"
sudo rm -rf "${SYSROOT_DIR}/etc/apt/sources.list.d/"*

# Fix symlinks to be relative
echo "Fixing symlinks..."
find "${SYSROOT_DIR}" -type l | while read symlink; do
    # Get the current target
    current_target=$(readlink "$symlink")
    
    # Skip if already relative
    if [[ "$current_target" != /* ]]; then
        continue
    fi
    
    # If target exists within our sysroot, make it relative
    if [[ -e "${SYSROOT_DIR}${current_target}" ]]; then
        link_dir=$(dirname "$symlink")
        relative_path=$(realpath --relative-to="$link_dir" "${SYSROOT_DIR}${current_target}")
        sudo ln -sf "$relative_path" "$symlink"
        echo "Fixed: $symlink -> $relative_path (was: $current_target)"
    else
        echo "Skipping - target outside sysroot: $symlink -> $current_target"
    fi
done

# Package sysroot
echo "Packaging sysroot..."
sudo tar -cJf "${OUTPUT_FILE}" -C "${SYSROOT_DIR}" .

# Cleanup temporary directory
echo "Cleaning up temporary directory..."
sudo rm -rf "${SYSROOT_DIR}"

echo "Sysroot created: ${OUTPUT_FILE}"
