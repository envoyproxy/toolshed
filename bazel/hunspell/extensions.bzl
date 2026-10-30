"""Module extension for prebuilt hunspell toolchains."""

load("//:versions.bzl", "VERSIONS")
load(
    "//hunspell/private:hunspell_prebuilt.bzl",
    "HUNSPELL_PREBUILT_STRIP_PREFIX",
    "HUNSPELL_PREBUILT_URL",
    "hunspell_prebuilt",
    "hunspell_toolchains_hub",
)
load("//private:extension_utils.bzl", "single_setup_tag")

_NO_OVERRIDE = "__envoy_toolshed_hunspell_default__"
DEFS_LABEL = str(Label("//hunspell:defs.bzl"))
TOOLCHAIN_TYPE_LABEL = str(Label("//hunspell:toolchain_type"))

def _hunspell_prebuilt_ext_impl(module_ctx):
    setup_tag = single_setup_tag(
        module_ctx = module_ctx,
        ext_name = "hunspell_prebuilt_extension",
        repos = "@hunspell_prebuilt_linux_x86_64, @hunspell_prebuilt_linux_aarch64, @hunspell_toolchains",
        attrs = ["linux_x86_64_sha256", "linux_aarch64_sha256"],
    )

    platform_labels = {}
    for platform in sorted(VERSIONS["hunspell_sha256"]):
        attr_name = platform.replace("-", "_") + "_sha256"
        override = getattr(setup_tag, attr_name) if setup_tag else _NO_OVERRIDE
        sha256 = VERSIONS["hunspell_sha256"][platform] if override == _NO_OVERRIDE else override
        if not sha256:
            continue
        repo_name = "hunspell_prebuilt_" + platform.replace("-", "_")
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

    hunspell_toolchains_hub(
        name = "hunspell_toolchains",
        defs_label = DEFS_LABEL,
        linux_aarch64 = platform_labels.get("linux-aarch64"),
        linux_x86_64 = platform_labels.get("linux-x86_64"),
        toolchain_type_label = TOOLCHAIN_TYPE_LABEL,
    )

# setup() controls per-platform prebuilt SHAs: unset uses VERSIONS["hunspell_sha256"],
# "" disables that prebuilt repo, and any other value overrides the sha256 for that platform.
_setup = tag_class(
    attrs = {
        "linux_aarch64_sha256": attr.string(
            default = _NO_OVERRIDE,
            doc = "SHA256 for the Linux aarch64 prebuilt hunspell artifact: unset uses VERSIONS[\"hunspell_sha256\"], \"\" disables the prebuilt repo for this platform, any other value overrides the sha256.",
        ),
        "linux_x86_64_sha256": attr.string(
            default = _NO_OVERRIDE,
            doc = "SHA256 for the Linux x86_64 prebuilt hunspell artifact: unset uses VERSIONS[\"hunspell_sha256\"], \"\" disables the prebuilt repo for this platform, any other value overrides the sha256.",
        ),
    },
)

hunspell_prebuilt_extension = module_extension(
    implementation = _hunspell_prebuilt_ext_impl,
    tag_classes = {"setup": _setup},
)
