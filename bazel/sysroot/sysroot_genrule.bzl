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
            # Use bash to execute the script (avoids chmod issues in read-only sandbox)
            # The script creates the tar file in the current working directory
            bash $$SCRIPT {} --output $$OUTPUT_DIR/sysroot-build
            # Move the generated tar file to Bazel's expected output location
            # The tar file is created in the current directory, not in SCRIPT_DIR
            mv {} $@
        """.format(build_args, output_file),
        tags = [
            "manual",
            "no-cache",
            "no-remote",
            "no-sandbox",  # Requires sudo, can't run in sandbox
        ],
        visibility = ["//visibility:public"],
        local = 1,  # Force local execution (no sandbox, no remote)
    )

def sysroots(matrix):
    """Create multiple sysroot genrules from a matrix configuration.
    
    This macro generates individual sysroot_genrule targets based on a matrix
    of configurations, similar to GitHub Actions matrix builds.
    
    Args:
        matrix: A list of dictionaries, where each dictionary contains:
            - arch: Architecture (amd64 or arm64)
            - glibc_version: glibc version (e.g., "2.31" or "2.28")
            - debian_version: Debian version (e.g., "bullseye" or "buster")
            - variant: Sysroot variant ("base" or "libstdcxx")
            - ppa_toolchain: (optional) Ubuntu PPA toolchain version
            - stdcc_version: (optional) libstdc++ version (default: "13")
    
    Example:
        sysroots([
            {
                "arch": "amd64",
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
        ])
    """
    
    # Collect all target names for the convenience filegroup
    target_names = []
    
    for config in matrix:
        arch = config["arch"]
        glibc_version = config["glibc_version"]
        debian_version = config["debian_version"]
        variant = config.get("variant", "base")
        ppa_toolchain = config.get("ppa_toolchain")
        stdcc_version = config.get("stdcc_version", "13")
        
        # Generate target name
        if variant == "libstdcxx":
            name = "sysroot_glibc{}_libstdcxx_{}".format(
                glibc_version.replace(".", ""),
                arch,
            )
        else:
            name = "sysroot_glibc{}_{}".format(
                glibc_version.replace(".", ""),
                arch,
            )
        
        # Create the genrule
        sysroot_genrule(
            name = name,
            arch = arch,
            glibc_version = glibc_version,
            debian_version = debian_version,
            variant = variant,
            ppa_toolchain = ppa_toolchain,
            stdcc_version = stdcc_version,
        )
        
        target_names.append(":" + name)
    
    # Create convenience filegroup to build all sysroots at once
    native.filegroup(
        name = "sysroots",
        srcs = target_names,
        tags = ["manual"],
        visibility = ["//visibility:public"],
    )
