"""Module extension for git prebuilt toolchains and shared CA bundle."""

load("//:versions.bzl", "VERSIONS")
load("//git/private:git_prebuilt.bzl", "GIT_PREBUILT_STRIP_PREFIX", "GIT_PREBUILT_URL", "git_cacert", "git_prebuilt", "git_toolchains_hub")
load("//git/private:git_source_hub.bzl", "git_source_hub")
load("//private:extension_utils.bzl", "single_setup_tag")

_NO_OVERRIDE = "__envoy_toolshed_git_default__"
DEFS_LABEL = str(Label("//git:defs.bzl"))
GCC_BUILD_LABEL = str(Label("//compile:gcc_build"))
GIT_PACKAGE_BZL_LABEL = str(Label("//git/private:git_package.bzl"))
GIT_SOURCE_BZL_LABEL = str(Label("//git/private:git_source.bzl"))
TOOLCHAIN_TYPE_LABEL = str(Label("//git:toolchain_type"))
TOOLCHAIN_BZL_LABEL = str(Label("//git:toolchain.bzl"))
_SOURCE_REPO_NAME = "envoy_toolshed_git_source"

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

def _git_source_ext_impl(module_ctx):
    setup_tag = single_setup_tag(
        module_ctx = module_ctx,
        ext_name = "git_source_extension",
        repos = "@envoy_toolshed_git_source",
        attrs = [
            "cacert",
            "git",
            "git_remote_http",
            "name",
            "ssl_lib",
            "stripper",
            "templates",
        ],
    )
    if not setup_tag:
        fail("git_source_extension requires setup()")

    git_source_hub(
        name = setup_tag.name,
        cacert = setup_tag.cacert,
        gcc_build_label = GCC_BUILD_LABEL,
        git = setup_tag.git,
        git_package_bzl_label = GIT_PACKAGE_BZL_LABEL,
        git_remote_http = setup_tag.git_remote_http,
        git_source_bzl_label = GIT_SOURCE_BZL_LABEL,
        ssl_lib = setup_tag.ssl_lib,
        stripper = setup_tag.stripper,
        templates = setup_tag.templates,
        toolchain_bzl_label = TOOLCHAIN_BZL_LABEL,
        toolchain_type_label = TOOLCHAIN_TYPE_LABEL,
    )

_source_setup = tag_class(
    attrs = {
        "cacert": attr.label(
            mandatory = True,
            doc = "CA bundle file used by the source git wrapper and packaging targets.",
        ),
        "git": attr.label(
            mandatory = True,
            doc = "Source-built git executable to wrap/package.",
        ),
        "git_remote_http": attr.label(
            mandatory = True,
            doc = "Source-built git-remote-http executable to wrap/package.",
        ),
        "name": attr.string(
            default = _SOURCE_REPO_NAME,
            doc = "Repository name for the generated source git hub.",
        ),
        "ssl_lib": attr.label(
            mandatory = True,
            doc = "Build setting forced to `openssl` for source git builds.",
        ),
        "stripper": attr.label(
            default = Label("//compile:llvm_minimal_host_llvm_strip"),
            doc = "Strip executable used when packaging git tarballs.",
        ),
        "templates": attr.label(
            mandatory = True,
            doc = "Template tree packaged alongside the git runtime.",
        ),
    },
)

git_source_extension = module_extension(
    implementation = _git_source_ext_impl,
    tag_classes = {"setup": _source_setup},
)
