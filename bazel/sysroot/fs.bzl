"""Macro for creating sysroot build genrules."""

def sysroot_daily_stamp(name = "sysroot_daily_stamp"):
    """Create a genrule that outputs today's UTC date, used to key sysroot cache entries.

    The output changes once per day (UTC), so sysroot targets built on the same day
    hit the remote cache, while a new day invalidates them and triggers a fresh build.
    The stamp is consumed only by sysroot genrules, so it does not perturb the action
    keys of any other targets.

    Args:
        name: Name of the genrule target (default: "sysroot_daily_stamp")
    """
    native.genrule(
        name = name,
        srcs = [],
        outs = [name + ".txt"],
        cmd = "date -u +%F > $@",
        tags = ["manual", "no-cache", "no-remote"],
        local = 1,
    )

def sysrootfs(
        name,
        arch,
        glibc_version,
        debian_version,
        stamp = ":sysroot_daily_stamp",
        tags = [
            "manual",
        ],
        extra_tags = [],
        visibility = ["//visibility:public"]):
    """Create a genrule to build a sysroot.

    Args:
        name: Name of the genrule target
        arch: Architecture (amd64 or arm64)
        glibc_version: glibc version (e.g., "2.31" or "2.28")
        debian_version: Debian version (e.g., "bullseye" or "buster")
        stamp: Label of a daily-stamp target whose content changes once per UTC day.
               Pass None to disable daily cache expiry.
    """

    output_file = "sysroot-glibc{}-{}.tar.xz".format(
        glibc_version,
        arch,
    )
    build_args = "--arch {} --glibc {} --debian {}".format(
        arch,
        glibc_version,
        debian_version,
    )

    native.genrule(
        name = name,
        srcs = [":build_sysroot.sh"] + ([stamp] if stamp else []),
        outs = [output_file],
        cmd = """
        set -e
        SCRIPT=$(location :build_sysroot.sh)
        OUTPUT_DIR=$$(mktemp -d)
        (bash $$SCRIPT {} --workdir $$OUTPUT_DIR/sysroot-build --output $@  > log.txt 2>&1) \
        || (cat log.txt && exit 1)
        """.format(build_args),
        # Requires sudo, can't run in sandbox
        tags = [
            "no-sandbox",
            "no-remote-exec",
        ] + tags + extra_tags,
        visibility = visibility,
    )

def sysroots(arches, glibc):
    """Generates matrix of sysroot targets.

    Args:
        arches: List of architectures (e.g. ["amd64", "arm64"])
        glibc: List of glibc versions (e.g. ["2.28", "2.31"])
    """
    target_names = []

    for arch in arches:
        for glibc_version in glibc:
            # 1. Infer Debian version based on glibc
            if glibc_version == "2.31":
                debian_version = "bullseye"
            elif glibc_version == "2.28":
                debian_version = "buster"
            else:
                fail("Unsupported glibc version: {}".format(glibc_version))
            name = "sysroot_glibc{v}_{a}".format(
                v = glibc_version.replace(".", ""),
                a = arch,
            )
            sysrootfs(
                name = name,
                arch = arch,
                glibc_version = glibc_version,
                debian_version = debian_version,
            )
            target_names.append(":" + name)

    native.filegroup(
        name = "sysroots",
        srcs = target_names,
        tags = ["manual"],
        visibility = ["//visibility:public"],
    )
