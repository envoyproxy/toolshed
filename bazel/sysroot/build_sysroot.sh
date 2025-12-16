#!/bin/bash

# Script to build a Debian sysroot for cross-compilation
# This is a non-hermetic build that uses debootstrap to create a minimal Debian system

set -e

# Parse command line arguments
ARCH=""
GLIBC_VERSION=""
DEBIAN_VERSION=""
VARIANT="base"
PPA_TOOLCHAIN=""
STDCC_VERSION="13"
OUTPUT_DIR="sysroot"

usage() {
    echo "Usage: $0 --arch <amd64|arm64> --glibc <version> --debian <version> [--variant <base|libstdcxx>] [--ppa-toolchain <version>] [--stdcc <version>] [--output <dir>]"
    echo ""
    echo "Options:"
    echo "  --arch           Architecture to build (amd64 or arm64)"
    echo "  --glibc          glibc version (e.g., 2.31 or 2.28)"
    echo "  --debian         Debian version (e.g., bullseye or buster)"
    echo "  --variant        Sysroot variant: base or libstdcxx (default: base)"
    echo "  --ppa-toolchain  Ubuntu PPA toolchain version (required for libstdcxx variant)"
    echo "  --stdcc          libstdc++ version (default: 13)"
    echo "  --output         Output directory name (default: sysroot)"
    exit 1
}

while [[ $# -gt 0 ]]; do
    case $1 in
        --arch)
            ARCH="$2"
            shift 2
            ;;
        --glibc)
            GLIBC_VERSION="$2"
            shift 2
            ;;
        --debian)
            DEBIAN_VERSION="$2"
            shift 2
            ;;
        --variant)
            VARIANT="$2"
            shift 2
            ;;
        --ppa-toolchain)
            PPA_TOOLCHAIN="$2"
            shift 2
            ;;
        --stdcc)
            STDCC_VERSION="$2"
            shift 2
            ;;
        --output)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            usage
            ;;
    esac
done

# Validate required arguments
if [[ -z "$ARCH" ]] || [[ -z "$GLIBC_VERSION" ]] || [[ -z "$DEBIAN_VERSION" ]]; then
    echo "Error: Missing required arguments"
    usage
fi

if [[ "$VARIANT" == "libstdcxx" ]] && [[ -z "$PPA_TOOLCHAIN" ]]; then
    echo "Error: --ppa-toolchain is required for libstdcxx variant"
    usage
fi

echo "Building sysroot with the following configuration:"
echo "  Architecture: $ARCH"
echo "  glibc version: $GLIBC_VERSION"
echo "  Debian version: $DEBIAN_VERSION"
echo "  Variant: $VARIANT"
echo "  Output directory: $OUTPUT_DIR"

# Determine Debian mirror and libgcc package based on Debian version
if [[ "$DEBIAN_VERSION" == "buster" ]]; then
    DEBIAN_MIRROR="http://archive.debian.org/debian/"
    LIBGCC_PACKAGE="libgcc1"  # buster uses old package name
else
    DEBIAN_MIRROR="http://deb.debian.org/debian/"
    LIBGCC_PACKAGE="libgcc-s1"  # bullseye and newer
fi

echo "  Debian mirror: $DEBIAN_MIRROR"
echo "  libgcc package: $LIBGCC_PACKAGE"

# Clean up any existing sysroot directory
if [[ -d "$OUTPUT_DIR" ]]; then
    echo "Removing existing sysroot directory..."
    sudo rm -rf "$OUTPUT_DIR"
fi

# Step 1: Create base sysroot with debootstrap
echo ""
echo "Step 1: Creating base sysroot with debootstrap..."
sudo debootstrap \
    --arch="$ARCH" \
    --variant=minbase \
    "$DEBIAN_VERSION" \
    "$OUTPUT_DIR" \
    "$DEBIAN_MIRROR"

# Step 2: Configure package sources
echo ""
echo "Step 2: Configuring package sources..."
echo "deb [check-valid-until=no] http://archive.debian.org/debian $DEBIAN_VERSION-backports main" \
    | sudo tee "$OUTPUT_DIR/etc/apt/sources.list.d/backports.list" > /dev/null

# Step 3: Update and install base packages
echo ""
echo "Step 3: Installing base packages..."
sudo chroot "$OUTPUT_DIR" apt-get -qq update
sudo chroot "$OUTPUT_DIR" apt-get -qq install --no-install-recommends -y \
    libc6 libc6-dev "$LIBGCC_PACKAGE" libxml2-dev
sudo chroot "$OUTPUT_DIR" apt-get -qq install --no-install-recommends -y \
    -t "$DEBIAN_VERSION-backports" linux-libc-dev

# Step 4: Install libstdc++ if requested
if [[ "$VARIANT" == "libstdcxx" ]]; then
    echo ""
    echo "Step 4: Installing libstdc++..."
    echo "deb http://ppa.launchpad.net/ubuntu-toolchain-r/test/ubuntu $PPA_TOOLCHAIN main" \
        | sudo tee "$OUTPUT_DIR/etc/apt/sources.list.d/toolchain.list" > /dev/null
    sudo apt-key --keyring "$OUTPUT_DIR/etc/apt/trusted.gpg" adv \
        --keyserver keyserver.ubuntu.com --recv-keys 1E9377A2BA9EF27F
    sudo chroot "$OUTPUT_DIR" apt-get -qq update
    sudo chroot "$OUTPUT_DIR" apt-get -qq install -y "libstdc++-${STDCC_VERSION}-dev"
fi

# Step 5: Cleanup sysroot
echo ""
echo "Step 5: Cleaning up sysroot..."
sudo chroot "$OUTPUT_DIR" apt-get clean

# Remove unnecessary directories
for dir in boot bin dev etc/alternatives etc/rmt etc/systemd etc/localtime \
           home media opt proc root run sbin srv sys tmp \
           usr/bin/awk usr/bin/nawk usr/bin/pager usr/bin/pidof usr/sbin \
           usr/share/doc usr/share/info usr/share/lintian usr/share/man usr/share/zoneinfo \
           var; do
    if [[ -e "$OUTPUT_DIR/$dir" ]]; then
        sudo rm -rf "$OUTPUT_DIR/$dir"
    fi
done

# Clean up apt sources
sudo rm -rf "$OUTPUT_DIR/etc/apt/sources.list.d/"*

# Step 6: Fix absolute symlinks to be relative
echo ""
echo "Step 6: Fixing absolute symlinks..."
find "$OUTPUT_DIR" -type l | while read symlink; do
    # Get the current target
    current_target=$(readlink "$symlink")

    # Skip if already relative
    if [[ "$current_target" != /* ]]; then
        continue
    fi

    # If target exists within our sysroot, make it relative
    if [[ -e "$OUTPUT_DIR$current_target" ]]; then
        link_dir=$(dirname "$symlink")
        relative_path=$(realpath --relative-to="$link_dir" "$OUTPUT_DIR$current_target")
        sudo ln -sf "$relative_path" "$symlink"
        echo "Fixed: $symlink -> $relative_path (was: $current_target)"
    else
        echo "Skipping - target outside sysroot: $symlink -> $current_target"
    fi
done

# Step 7: Package the sysroot
echo ""
echo "Step 7: Packaging sysroot..."
if [[ "$VARIANT" == "libstdcxx" ]]; then
    OUTPUT_FILE="sysroot-glibc${GLIBC_VERSION}-libstdc++${STDCC_VERSION}-${ARCH}.tar.xz"
else
    OUTPUT_FILE="sysroot-glibc${GLIBC_VERSION}-${ARCH}.tar.xz"
fi

sudo tar -cJf "$OUTPUT_FILE" -C "$OUTPUT_DIR" .
echo ""
echo "Successfully built sysroot: $OUTPUT_FILE"
echo "Size: $(du -h "$OUTPUT_FILE" | cut -f1)"
