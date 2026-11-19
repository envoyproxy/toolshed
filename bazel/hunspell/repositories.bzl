"""WORKSPACE repository setup for the hunspell toolchains."""

load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive")
load(
    "//hunspell/private:hunspell_prebuilt.bzl",
    "HUNSPELL_PREBUILT_STRIP_PREFIX",
    "HUNSPELL_PREBUILT_URL",
    "hunspell_prebuilt",
    "hunspell_toolchains_hub",
)
load("//:versions.bzl", "VERSIONS")

def setup_hunspell():
    """Creates the WORKSPACE repositories required by `//hunspell`.

    The prebuilts for Linux, and the hunspell source and en_US dictionary for the source toolchain
    that `load_hunspell_toolchains` registers as a fallback (fetched only if it is used).
    """
    platform_labels = {}
    for platform in sorted(VERSIONS["hunspell_sha256"]):
        sha256 = VERSIONS["hunspell_sha256"][platform]
        if not sha256:
            continue
        repo_name = "hunspell_prebuilt_" + platform.replace("-", "_")
        if repo_name not in native.existing_rules():
            hunspell_prebuilt(
                name = repo_name,
                sha256 = sha256,
                strip_prefix = HUNSPELL_PREBUILT_STRIP_PREFIX.format(
                    platform = platform,
                    version = VERSIONS["hunspell"]["version"],
                ),
                url = HUNSPELL_PREBUILT_URL.format(
                    bins_release = VERSIONS["bins_release"],
                    platform = platform,
                    version = VERSIONS["hunspell"]["version"],
                ),
            )
        platform_labels[platform] = "@%s//:BUILD.bazel" % repo_name

    if "hunspell_toolchains" not in native.existing_rules():
        hunspell_toolchains_hub(
            name = "hunspell_toolchains",
            defs_label = "@envoy_toolshed//hunspell:defs.bzl",
            linux_aarch64 = platform_labels.get("linux-aarch64"),
            linux_x86_64 = platform_labels.get("linux-x86_64"),
            toolchain_type_label = "@envoy_toolshed//hunspell:toolchain_type",
        )

    if "hunspell_src" not in native.existing_rules():
        http_archive(
            name = "hunspell_src",
            build_file = "@envoy_toolshed//hunspell/private:hunspell.BUILD.bazel",
            sha256 = VERSIONS["hunspell"]["sha256"],
            strip_prefix = "hunspell-%s" % VERSIONS["hunspell"]["version"],
            url = "https://github.com/hunspell/hunspell/releases/download/v{version}/hunspell-{version}.tar.gz".format(
                version = VERSIONS["hunspell"]["version"],
            ),
        )

    if "dictionary_en" not in native.existing_rules():
        http_archive(
            name = "dictionary_en",
            build_file = "@envoy_toolshed//hunspell/private:dictionary_en.BUILD.bazel",
            sha256 = VERSIONS["dictionary_en"]["sha256"],
            strip_prefix = "package",
            url = "https://registry.npmjs.org/dictionary-en/-/dictionary-en-%s.tgz" % VERSIONS["dictionary_en"]["version"],
        )

def load_hunspell_toolchains():
    """Registers the hunspell toolchains for WORKSPACE users.

    The prebuilts first, so that they win where they match, then the source build, as a fallback
    for platforms without a prebuilt (eg macOS).
    """
    native.register_toolchains(
        "@hunspell_toolchains//:all",
        "@envoy_toolshed//hunspell/source:source_toolchain_linux",
        "@envoy_toolshed//hunspell/source:source_toolchain_macos",
    )
