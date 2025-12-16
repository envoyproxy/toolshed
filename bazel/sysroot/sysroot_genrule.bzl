"""Macro for creating sysroot build genrules."""

def sysroot_genrule(
        name,
        arch,
        glibc_version,
        debian_version,
        variant = "base",
        ppa_toolchain = None,
        stdcc_version = "13"):
    """Create a genrule to build a sysroot.
    
    Args:
        name: Name of the genrule target
        arch: Architecture (amd64 or arm64)
        glibc_version: glibc version (e.g., "2.31" or "2.28")
        debian_version: Debian version (e.g., "bullseye" or "buster")
        variant: Sysroot variant ("base" or "libstdcxx")
        ppa_toolchain: Ubuntu PPA toolchain version (required for libstdcxx variant)
        stdcc_version: libstdc++ version (default: "13")
    """
    
    # Construct output filename
    if variant == "libstdcxx":
        output_file = "sysroot-glibc{}-libstdc++{}-{}.tar.xz".format(
            glibc_version,
            stdcc_version,
            arch,
        )
        build_args = "--arch {} --glibc {} --debian {} --variant {} --ppa-toolchain {} --stdcc {}".format(
            arch,
            glibc_version,
            debian_version,
            variant,
            ppa_toolchain,
            stdcc_version,
        )
    else:
        output_file = "sysroot-glibc{}-{}.tar.xz".format(
            glibc_version,
            arch,
        )
        build_args = "--arch {} --glibc {} --debian {} --variant {}".format(
            arch,
            glibc_version,
            debian_version,
            variant,
        )
    
    native.genrule(
        name = name,
        srcs = [":build_sysroot.sh"],
        outs = [output_file],
        cmd = """
            set -e
            SCRIPT=$(location :build_sysroot.sh)
            OUTPUT_DIR=$$(mktemp -d)
            cd $$(dirname $$SCRIPT)
            chmod +x build_sysroot.sh
            ./build_sysroot.sh {} --output $$OUTPUT_DIR/sysroot-build
            mv {} $@
        """.format(build_args, output_file),
        tags = [
            "manual",
            "no-cache",
            "no-remote",
        ],
        visibility = ["//visibility:public"],
    )
