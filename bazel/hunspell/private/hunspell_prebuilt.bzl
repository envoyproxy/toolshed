"""Repository rules for prebuilt hunspell toolchains."""

HUNSPELL_PREBUILT_URL = "https://github.com/envoyproxy/toolshed/releases/download/bins-v{bins_release}/hunspell-{version}-{platform}.tar.zst"
HUNSPELL_PREBUILT_STRIP_PREFIX = "hunspell-{version}-{platform}"

_PLATFORM_TARGETS = {
    "linux-aarch64": {
        "constraint": "@platforms//cpu:aarch64",
        "name": "linux_aarch64",
    },
    "linux-x86_64": {
        "constraint": "@platforms//cpu:x86_64",
        "name": "linux_x86_64",
    },
}

def render_hunspell_toolchains_build(platform_repos, defs_label, toolchain_type_label):
    """Render the hub BUILD file for the configured prebuilt toolchains.

    Args:
        platform_repos: Mapping from platform suffix to prebuilt repository name.
        defs_label: Canonical label string for //hunspell:defs.bzl.
        toolchain_type_label: Canonical label string for //hunspell:toolchain_type.

    Returns:
        BUILD file content for the hub repository.
    """
    lines = [
        "load(\"%s\", \"hunspell_toolchain\")" % defs_label,
        "",
    ]
    for platform in sorted(_PLATFORM_TARGETS):
        repo_name = platform_repos.get(platform)
        if not repo_name:
            continue
        target = _PLATFORM_TARGETS[platform]
        lines.extend([
            "hunspell_toolchain(",
            "    name = \"%s_impl\"," % target["name"],
            # workspace_name is canonical here, so the hub must render @@ labels.
            "    affix = \"@" + "@%s//:share/hunspell/en_US.aff\"," % repo_name,
            "    dictionary = \"@" + "@%s//:share/hunspell/en_US.dic\"," % repo_name,
            "    hunspell = \"@" + "@%s//:hunspell\"," % repo_name,
            ")",
            "",
            "toolchain(",
            "    name = \"%s\"," % target["name"],
            "    toolchain = \":%s_impl\"," % target["name"],
            "    toolchain_type = \"%s\"," % toolchain_type_label,
            "    exec_compatible_with = [",
            "        \"@platforms//os:linux\",",
            "        \"%s\"," % target["constraint"],
            "    ],",
            ")",
            "",
        ])
    return "\n".join(lines)

def _hunspell_prebuilt_impl(ctx):
    if not ctx.attr.sha256:
        fail("hunspell_prebuilt requires a non-empty sha256")
    ctx.download_and_extract(
        url = ctx.attr.url,
        sha256 = ctx.attr.sha256,
        stripPrefix = ctx.attr.strip_prefix,
    )
    return ctx.repo_metadata(reproducible = True)

hunspell_prebuilt = repository_rule(
    implementation = _hunspell_prebuilt_impl,
    attrs = {
        "sha256": attr.string(mandatory = True),
        "strip_prefix": attr.string(mandatory = True),
        "url": attr.string(mandatory = True),
    },
)

def _hunspell_toolchains_hub_impl(ctx):
    ctx.file("BUILD.bazel", render_hunspell_toolchains_build(
        {
            "linux-aarch64": ctx.attr.linux_aarch64.workspace_name if ctx.attr.linux_aarch64 else None,
            "linux-x86_64": ctx.attr.linux_x86_64.workspace_name if ctx.attr.linux_x86_64 else None,
        },
        ctx.attr.defs_label,
        ctx.attr.toolchain_type_label,
    ))
    return ctx.repo_metadata(reproducible = True)

hunspell_toolchains_hub = repository_rule(
    implementation = _hunspell_toolchains_hub_impl,
    attrs = {
        "defs_label": attr.string(mandatory = True),
        "linux_aarch64": attr.label(default = None),
        "linux_x86_64": attr.label(default = None),
        "toolchain_type_label": attr.string(mandatory = True),
    },
)
