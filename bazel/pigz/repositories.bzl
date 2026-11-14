"""WORKSPACE repository setup for the prebuilt pigz toolchains."""

load("//:versions.bzl", "VERSIONS")
load(
    "//pigz/private:pigz_prebuilt.bzl",
    "PIGZ_PREBUILT_STRIP_PREFIX",
    "PIGZ_PREBUILT_URL",
    "pigz_prebuilt",
    "pigz_toolchains_hub",
)

def setup_pigz(host_path = ""):
    """Creates the WORKSPACE repositories required by `//pigz`.

    Args:
        host_path: Absolute path of a pigz on the host (eg `/usr/bin/pigz`), for a toolchain for
            the host's OS and CPU, where there is no prebuilt for it. The binary runs where the
            action does, so it must run there (eg for remote execution).
    """
    platform_labels = {}
    for platform in sorted(VERSIONS["pigz_sha256"]):
        sha256 = VERSIONS["pigz_sha256"][platform]
        if not sha256:
            continue
        repo_name = "pigz_prebuilt_" + platform.replace("-", "_")
        if repo_name not in native.existing_rules():
            pigz_prebuilt(
                name = repo_name,
                sha256 = sha256,
                strip_prefix = PIGZ_PREBUILT_STRIP_PREFIX.format(
                    platform = platform,
                    version = VERSIONS["pigz"],
                ),
                url = PIGZ_PREBUILT_URL.format(
                    bins_release = VERSIONS["bins_release"],
                    platform = platform,
                    version = VERSIONS["pigz"],
                ),
            )
        platform_labels[platform] = "@%s//:BUILD.bazel" % repo_name

    if "pigz_toolchains" not in native.existing_rules():
        pigz_toolchains_hub(
            name = "pigz_toolchains",
            defs_label = "@envoy_toolshed//pigz:defs.bzl",
            host_path = host_path,
            linux_aarch64 = platform_labels.get("linux-aarch64"),
            linux_x86_64 = platform_labels.get("linux-x86_64"),
            toolchain_type_label = "@envoy_toolshed//pigz:toolchain_type",
        )

def load_pigz_toolchains():
    """Registers the pigz toolchains for WORKSPACE users.

    The prebuilts (and a host pigz, if `setup_pigz` was given one), then a toolchain that fails,
    naming the platform without a pigz. Register a source toolchain before calling this to build
    pigz where there is no prebuilt (see `//pigz:README.md`).
    """
    native.register_toolchains(
        "@pigz_toolchains//:all",
        "@envoy_toolshed//pigz:unavailable_toolchain",
    )
