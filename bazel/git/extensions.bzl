"""Module extension for git prebuilt toolchains and shared CA bundle."""

load("//:versions.bzl", "VERSIONS")
load("//git/private:git_prebuilt.bzl", "GIT_PREBUILT_STRIP_PREFIX", "GIT_PREBUILT_URL", "git_cacert", "git_prebuilt", "git_toolchains_hub")
load("//private:extension_utils.bzl", "single_setup_tag")

_NO_OVERRIDE = "__envoy_toolshed_git_default__"
DEFS_LABEL = str(Label("//git:defs.bzl"))
TOOLCHAIN_TYPE_LABEL = str(Label("//git:toolchain_type"))

def _git_prebuilt_ext_impl(module_ctx):
    setup_tag = single_setup_tag(
        module_ctx = module_ctx,
        ext_name = "git_prebuilt_extension",
        repos = "@cacert, @git_prebuilt_linux_x86_64, @git_prebuilt_linux_aarch64, @git_toolchains",
        attrs = ["linux_x86_64_sha256", "linux_aarch64_sha256"],
    )

    cacert = VERSIONS["cacert"]
    git_cacert(
        name = "cacert",
        sha256 = cacert["sha256"],
        url = cacert["url"].format(version = cacert["version"]),
    )

    platform_labels = {}
    for platform in sorted(VERSIONS["git_sha256"]):
        attr_name = platform.replace("-", "_") + "_sha256"
        override = getattr(setup_tag, attr_name) if setup_tag else _NO_OVERRIDE
        sha256 = VERSIONS["git_sha256"][platform] if override == _NO_OVERRIDE else override
        if not sha256:
            continue
        repo_name = "git_prebuilt_" + platform.replace("-", "_")
        git_prebuilt(
            name = repo_name,
            sha256 = sha256,
            strip_prefix = GIT_PREBUILT_STRIP_PREFIX.format(
                platform = platform,
                version = VERSIONS["git"],
            ),
            url = GIT_PREBUILT_URL.format(
                bins_release = VERSIONS["bins_release"],
                platform = platform,
                version = VERSIONS["git"],
            ),
        )
        platform_labels[platform] = "@%s//:BUILD.bazel" % repo_name

    git_toolchains_hub(
        name = "git_toolchains",
        defs_label = DEFS_LABEL,
        linux_aarch64 = platform_labels.get("linux-aarch64"),
        linux_x86_64 = platform_labels.get("linux-x86_64"),
        toolchain_type_label = TOOLCHAIN_TYPE_LABEL,
    )

# setup() controls per-platform prebuilt SHAs: unset uses VERSIONS["git_sha256"],
# "" disables that prebuilt repo (source fallback only), and any other value
# overrides the sha256 for that platform.
_setup = tag_class(
    attrs = {
        "linux_aarch64_sha256": attr.string(
            default = _NO_OVERRIDE,
            doc = "SHA256 for the Linux aarch64 prebuilt git artifact: unset uses VERSIONS[\"git_sha256\"], \"\" disables the prebuilt repo for this platform, any other value overrides the sha256.",
        ),
        "linux_x86_64_sha256": attr.string(
            default = _NO_OVERRIDE,
            doc = "SHA256 for the Linux x86_64 prebuilt git artifact: unset uses VERSIONS[\"git_sha256\"], \"\" disables the prebuilt repo for this platform, any other value overrides the sha256.",
        ),
    },
)

git_prebuilt_extension = module_extension(
    implementation = _git_prebuilt_ext_impl,
    tag_classes = {"setup": _setup},
)
