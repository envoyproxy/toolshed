"""Module extensions for sq prebuilt and source toolchains."""

load("//:versions.bzl", "VERSIONS")
load("//pgp/private:sq_prebuilt.bzl", "SQ_PREBUILT_STRIP_PREFIX", "SQ_PREBUILT_URL", "sq_prebuilt", "sq_toolchains_hub")
load("//pgp/private:sq_source_hub.bzl", "sq_source_hub")
load("//private:extension_utils.bzl", "single_setup_tag")

_NO_OVERRIDE = "__envoy_toolshed_sq_default__"
DEFS_LABEL = str(Label("//pgp:defs.bzl"))
SQ_PACKAGE_BZL_LABEL = str(Label("//pgp/private:sq_package.bzl"))
TOOLCHAIN_TYPE_LABEL = str(Label("//pgp:toolchain_type"))
_SOURCE_REPO_NAME = "envoy_toolshed_sq_source"
_PLATFORMS = {
    "Linux-ARM64": struct(
        attr = "linux_aarch64_sha256",
        repo = "sq_prebuilt_linux_aarch64",
    ),
    "Linux-X64": struct(
        attr = "linux_x86_64_sha256",
        repo = "sq_prebuilt_linux_x86_64",
    ),
}

def _sq_prebuilt_ext_impl(module_ctx):
    setup_tag = single_setup_tag(
        module_ctx = module_ctx,
        ext_name = "sq_prebuilt_extension",
        repos = "@sq_prebuilt_linux_x86_64, @sq_prebuilt_linux_aarch64, @sq_toolchains",
        attrs = ["linux_x86_64_sha256", "linux_aarch64_sha256"],
    )

    platform_labels = {}
    for platform in sorted(VERSIONS["sq_sha256"]):
        if platform not in _PLATFORMS:
            fail("Unhandled sq prebuilt platform in VERSIONS[\"sq_sha256\"]: %s" % platform)
        platform_info = _PLATFORMS[platform]
        override = getattr(setup_tag, platform_info.attr) if setup_tag else _NO_OVERRIDE
        sha256 = VERSIONS["sq_sha256"][platform] if override == _NO_OVERRIDE else override
        if not sha256:
            continue
        sq_prebuilt(
            name = platform_info.repo,
            sha256 = sha256,
            strip_prefix = SQ_PREBUILT_STRIP_PREFIX.format(
                platform = platform,
                version = VERSIONS["sq"],
            ),
            url = SQ_PREBUILT_URL.format(
                bins_release = VERSIONS["bins_release"],
                platform = platform,
                version = VERSIONS["sq"],
            ),
        )
        platform_labels[platform] = "@%s//:BUILD.bazel" % platform_info.repo

    sq_toolchains_hub(
        name = "sq_toolchains",
        defs_label = DEFS_LABEL,
        linux_aarch64 = platform_labels.get("Linux-ARM64"),
        linux_x86_64 = platform_labels.get("Linux-X64"),
        toolchain_type_label = TOOLCHAIN_TYPE_LABEL,
    )

# setup() controls per-platform prebuilt SHAs: unset uses VERSIONS["sq_sha256"],
# "" disables that prebuilt repo (source fallback only), and any other value
# overrides the sha256 for that platform.
_setup = tag_class(
    attrs = {
        "linux_aarch64_sha256": attr.string(
            default = _NO_OVERRIDE,
            doc = "SHA256 for the Linux aarch64 prebuilt sq artifact: unset uses VERSIONS[\"sq_sha256\"], \"\" disables the prebuilt repo for this platform, any other value overrides the sha256.",
        ),
        "linux_x86_64_sha256": attr.string(
            default = _NO_OVERRIDE,
            doc = "SHA256 for the Linux x86_64 prebuilt sq artifact: unset uses VERSIONS[\"sq_sha256\"], \"\" disables the prebuilt repo for this platform, any other value overrides the sha256.",
        ),
    },
)

sq_prebuilt_extension = module_extension(
    implementation = _sq_prebuilt_ext_impl,
    tag_classes = {"setup": _setup},
)

def _sq_source_ext_impl(module_ctx):
    setup_tag = single_setup_tag(
        module_ctx = module_ctx,
        ext_name = "sq_source_extension",
        repos = "@envoy_toolshed_sq_source",
        attrs = [
            "name",
            "sq",
            "stripper",
        ],
    )
    if not setup_tag:
        fail("sq_source_extension requires setup()")

    sq_source_hub(
        name = setup_tag.name,
        defs_bzl_label = DEFS_LABEL,
        sq = setup_tag.sq,
        sq_package_bzl_label = SQ_PACKAGE_BZL_LABEL,
        stripper = setup_tag.stripper,
        toolchain_type_label = TOOLCHAIN_TYPE_LABEL,
    )

_source_setup = tag_class(
    attrs = {
        "name": attr.string(
            default = _SOURCE_REPO_NAME,
            doc = "Repository name for the generated source sq hub.",
        ),
        "sq": attr.label(
            default = "@sq//:sq_from_source",
            doc = "Source-built sq executable to wrap/package.",
        ),
        "stripper": attr.label(
            default = Label("//compile:llvm_minimal_host_llvm_strip"),
            doc = "Strip executable used when packaging sq tarballs.",
        ),
    },
)

sq_source_extension = module_extension(
    implementation = _sq_source_ext_impl,
    tag_classes = {"setup": _source_setup},
)
