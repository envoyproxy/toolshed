"""Sysroot configuration.

This file defines the sysroot variants to build.
Edit this file to add, remove, or modify sysroot configurations.
"""

SYSROOT_CONFIG = [
    # glibc 2.31 (current) - Debian bullseye
    {
        "arch": "amd64",
        "glibc_version": "2.31",
        "debian_version": "bullseye",
        "variant": "base",
    },
    {
        "arch": "arm64",
        "glibc_version": "2.31",
        "debian_version": "bullseye",
        "variant": "base",
    },
    {
        "arch": "amd64",
        "glibc_version": "2.31",
        "debian_version": "bullseye",
        "variant": "libstdcxx",
        "ppa_toolchain": "focal",
        "stdcc_version": "13",
    },
    {
        "arch": "arm64",
        "glibc_version": "2.31",
        "debian_version": "bullseye",
        "variant": "libstdcxx",
        "ppa_toolchain": "focal",
        "stdcc_version": "13",
    },
    # glibc 2.28 (older) - Debian buster for Ubuntu 18.04/RHEL 8 compatibility
    {
        "arch": "amd64",
        "glibc_version": "2.28",
        "debian_version": "buster",
        "variant": "base",
    },
    {
        "arch": "arm64",
        "glibc_version": "2.28",
        "debian_version": "buster",
        "variant": "base",
    },
    {
        "arch": "amd64",
        "glibc_version": "2.28",
        "debian_version": "buster",
        "variant": "libstdcxx",
        "ppa_toolchain": "bionic",
        "stdcc_version": "13",
    },
    {
        "arch": "arm64",
        "glibc_version": "2.28",
        "debian_version": "buster",
        "variant": "libstdcxx",
        "ppa_toolchain": "bionic",
        "stdcc_version": "13",
    },
]
