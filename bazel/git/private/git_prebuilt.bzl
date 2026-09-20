"""Repository rules for prebuilt git toolchains and shared CA bundle."""

GIT_PREBUILT_URL = "https://github.com/envoyproxy/toolshed/releases/download/bins-v{bins_release}/git-{version}-{platform}.tar.zst"
GIT_PREBUILT_STRIP_PREFIX = "git-{version}-{platform}"

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

def render_git_toolchains_build(platform_repos):
    """Render the hub BUILD file for the configured prebuilt toolchains.

    Args:
        platform_repos: Mapping from platform suffix to prebuilt repository name.

    Returns:
        BUILD file content for the hub repository.
    """
    lines = [
        "load(\"@envoy_toolshed//git:defs.bzl\", \"git_toolchain\")",
        "",
    ]
    for platform in sorted(_PLATFORM_TARGETS):
        repo_name = platform_repos.get(platform)
        if not repo_name:
            continue
        target = _PLATFORM_TARGETS[platform]
        lines.extend([
            "git_toolchain(",
            "    name = \"%s_impl\"," % target["name"],
            "    git = \"@%s//:git\"," % repo_name,
            "    data = [\"@%s//:runtime\"]," % repo_name,
            ")",
            "",
            "toolchain(",
            "    name = \"%s\"," % target["name"],
            "    toolchain = \":%s_impl\"," % target["name"],
            "    toolchain_type = \"@envoy_toolshed//git:toolchain_type\",",
            "    exec_compatible_with = [",
            "        \"@platforms//os:linux\",",
            "        \"%s\"," % target["constraint"],
            "    ],",
            ")",
            "",
        ])
    return "\n".join(lines)

def _git_prebuilt_impl(ctx):
    if not ctx.attr.sha256:
        fail("git_prebuilt requires a non-empty sha256")
    ctx.download_and_extract(
        url = ctx.attr.url,
        sha256 = ctx.attr.sha256,
        stripPrefix = ctx.attr.strip_prefix,
    )
    return ctx.repo_metadata(reproducible = True)

git_prebuilt = repository_rule(
    implementation = _git_prebuilt_impl,
    attrs = {
        "sha256": attr.string(mandatory = True),
        "strip_prefix": attr.string(mandatory = True),
        "url": attr.string(mandatory = True),
    },
)

def _repo_name(label):
    return label.workspace_name

def _git_toolchains_hub_impl(ctx):
    ctx.file("BUILD.bazel", render_git_toolchains_build({
        "linux-aarch64": _repo_name(ctx.attr.linux_aarch64) if ctx.attr.linux_aarch64 else None,
        "linux-x86_64": _repo_name(ctx.attr.linux_x86_64) if ctx.attr.linux_x86_64 else None,
    }))
    return ctx.repo_metadata(reproducible = True)

git_toolchains_hub = repository_rule(
    implementation = _git_toolchains_hub_impl,
    attrs = {
        "linux_aarch64": attr.label(default = None),
        "linux_x86_64": attr.label(default = None),
    },
)

def _git_cacert_impl(ctx):
    ctx.download(
        url = ctx.attr.url,
        output = "file/cacert.pem",
        sha256 = ctx.attr.sha256,
    )
    ctx.file(
        "file/BUILD.bazel",
        """exports_files([\"cacert.pem\"])\nfilegroup(name = \"file\", srcs = [\"cacert.pem\"], visibility = [\"//visibility:public\"])\n""",
    )
    return ctx.repo_metadata(reproducible = True)

git_cacert = repository_rule(
    implementation = _git_cacert_impl,
    attrs = {
        "sha256": attr.string(mandatory = True),
        "url": attr.string(mandatory = True),
    },
)
