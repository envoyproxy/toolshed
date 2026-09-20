"""Module extension for git prebuilt toolchains and shared CA bundle."""

load("//:versions.bzl", "VERSIONS")
load("//git/private:git_prebuilt.bzl", "GIT_PREBUILT_STRIP_PREFIX", "GIT_PREBUILT_URL", "git_cacert", "git_prebuilt", "git_toolchains_hub")

_NO_OVERRIDE = "__envoy_toolshed_git_default__"

def _single_setup_tag(module_ctx, ext_name, repos, attrs):
    tags = [
        tag
        for mod in module_ctx.modules
        for tag in mod.tags.setup
    ]
    if not tags:
        return None
    chosen = tags[0]
    for tag in tags[1:]:
        for attr_name in attrs:
            if getattr(tag, attr_name) == getattr(chosen, attr_name):
                continue
            fail(
                (("Conflicting setup() calls found for %s. " +
                  "Repository names are fixed to %s, so all modules " +
                  "must request identical configuration " +
                  "(differing attribute: %s).") % (ext_name, repos, attr_name)),
            )
    return chosen

def _git_prebuilt_ext_impl(module_ctx):
    setup_tag = _single_setup_tag(
        module_ctx,
        "git_prebuilt_extension",
        "@cacert, @git_prebuilt_linux_x86_64, @git_prebuilt_linux_aarch64, @git_toolchains",
        ["linux_x86_64_sha256", "linux_aarch64_sha256"],
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
        linux_aarch64 = platform_labels.get("linux-aarch64"),
        linux_x86_64 = platform_labels.get("linux-x86_64"),
    )

_setup = tag_class(
    attrs = {
        "linux_aarch64_sha256": attr.string(
            default = _NO_OVERRIDE,
            doc = "SHA256 hash of the prebuilt Linux aarch64 git artifact. Set to an empty string to disable this repo.",
        ),
        "linux_x86_64_sha256": attr.string(
            default = _NO_OVERRIDE,
            doc = "SHA256 hash of the prebuilt Linux x86_64 git artifact. Set to an empty string to disable this repo.",
        ),
    },
)

git_prebuilt_extension = module_extension(
    implementation = _git_prebuilt_ext_impl,
    tag_classes = {"setup": _setup},
)
