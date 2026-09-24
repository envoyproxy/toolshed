"""Repository rules for prebuilt sq toolchains."""

SQ_PREBUILT_URL = "https://github.com/envoyproxy/toolshed/releases/download/bins-v{bins_release}/sq-{version}-{platform}.tar.zst"
SQ_PREBUILT_STRIP_PREFIX = "sq-{version}-{platform}"

_PLATFORM_TARGETS = {
    "Linux-ARM64": {
        "constraint": "@platforms//cpu:aarch64",
        "name": "linux_aarch64",
    },
    "Linux-X64": {
        "constraint": "@platforms//cpu:x86_64",
        "name": "linux_x86_64",
    },
}

def render_sq_toolchains_build(platform_repos, defs_label, toolchain_type_label):
    """Render the hub BUILD file for the configured prebuilt sq toolchains."""
    lines = [
        "load(\"%s\", \"pgp_toolchain\", \"sq_signer\")" % defs_label,
        "",
    ]
    for platform in sorted(_PLATFORM_TARGETS):
        repo_name = platform_repos.get(platform)
        if not repo_name:
            continue
        target = _PLATFORM_TARGETS[platform]
        lines.extend([
            "sq_signer(",
            "    name = \"%s_signer\"," % target["name"],
            "    sq = \"@" + "@%s//:sq\"," % repo_name,
            ")",
            "",
            "pgp_toolchain(",
            "    name = \"%s_impl\"," % target["name"],
            "    signer = \":%s_signer\"," % target["name"],
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

def _sq_prebuilt_impl(ctx):
    if not ctx.attr.sha256:
        fail("sq_prebuilt requires a non-empty sha256")
    ctx.download_and_extract(
        url = ctx.attr.url,
        sha256 = ctx.attr.sha256,
        stripPrefix = ctx.attr.strip_prefix,
    )
    return ctx.repo_metadata(reproducible = True)

sq_prebuilt = repository_rule(
    implementation = _sq_prebuilt_impl,
    attrs = {
        "sha256": attr.string(mandatory = True),
        "strip_prefix": attr.string(mandatory = True),
        "url": attr.string(mandatory = True),
    },
)

def _repo_name(label):
    return label.workspace_name

def _sq_toolchains_hub_impl(ctx):
    ctx.file("BUILD.bazel", render_sq_toolchains_build(
        {
            "Linux-ARM64": _repo_name(ctx.attr.linux_aarch64) if ctx.attr.linux_aarch64 else None,
            "Linux-X64": _repo_name(ctx.attr.linux_x86_64) if ctx.attr.linux_x86_64 else None,
        },
        ctx.attr.defs_label,
        ctx.attr.toolchain_type_label,
    ))
    return ctx.repo_metadata(reproducible = True)

sq_toolchains_hub = repository_rule(
    implementation = _sq_toolchains_hub_impl,
    attrs = {
        "defs_label": attr.string(mandatory = True),
        "linux_aarch64": attr.label(default = None),
        "linux_x86_64": attr.label(default = None),
        "toolchain_type_label": attr.string(mandatory = True),
    },
)
