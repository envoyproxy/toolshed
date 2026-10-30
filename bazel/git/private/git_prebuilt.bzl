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

# Host platforms the hub may fall back to the host's git on. Linux always has a
# prebuilt (or the source fallback), and Windows is untested.
_HOST_FALLBACK_OS_CONSTRAINTS = {
    "macos": "@platforms//os:macos",
}

_CPU_CONSTRAINTS = {
    "aarch64": "@platforms//cpu:aarch64",
    "x86_64": "@platforms//cpu:x86_64",
}

_CPU_ALIASES = {
    "aarch64": "aarch64",
    "amd64": "x86_64",
    "arm64": "aarch64",
    "x86_64": "x86_64",
}

def host_fallback_platform(host):
    """Return `host` if the hub may fall back to the host's git on it, else None.

    Args:
        host: Platform suffix from `host_platform`, or None.

    Returns:
        `host` when it never has a prebuilt and its OS supports the fallback, else None.
    """
    if not host or host in _PLATFORM_TARGETS:
        return None
    if host.split("-", 1)[0] not in _HOST_FALLBACK_OS_CONSTRAINTS:
        return None
    return host

def host_platform(os_name, arch):
    """Map a `repository_os` name and arch to a `<os>-<cpu>` platform suffix.

    Args:
        os_name: `repository_ctx.os.name`, eg `mac os x` or `linux`.
        arch: `repository_ctx.os.arch`, eg `aarch64` or `amd64`.

    Returns:
        The platform suffix (eg `macos-aarch64`), or None for an unknown OS or CPU.
    """
    os_name = os_name.lower()
    if os_name.startswith("mac"):
        os_key = "macos"
    elif os_name.startswith("linux"):
        os_key = "linux"
    elif os_name.startswith("windows"):
        os_key = "windows"
    else:
        return None
    cpu = _CPU_ALIASES.get(arch.lower())
    if not cpu:
        return None
    return "%s-%s" % (os_key, cpu)

def render_git_toolchains_build(platform_repos, defs_label, toolchain_type_label, host = None):
    """Render the hub BUILD file for the configured prebuilt toolchains.

    Args:
        platform_repos: Mapping from platform suffix to prebuilt repository name.
        defs_label: Canonical label string for //git:defs.bzl.
        toolchain_type_label: Canonical label string for //git:toolchain_type.
        host: Platform suffix of the host (eg `macos-aarch64`) to render a toolchain for using
            the hub's `host/git` (a symlink to the host's git), or None. Ignored unless
            `host_fallback_platform` accepts it.

    Returns:
        BUILD file content for the hub repository.
    """
    lines = [
        "load(\"%s\", \"git_toolchain\")" % defs_label,
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
            # workspace_name is canonical here, so the hub must render @@ labels.
            "    git = \"@" + "@%s//:git\"," % repo_name,
            "    data = [\"@" + "@%s//:runtime\"]," % repo_name,
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
    if host_fallback_platform(host):
        os_key, cpu = host.split("-", 1)
        lines.extend(host_toolchain_lines(
            toolchain_type_label,
            [_HOST_FALLBACK_OS_CONSTRAINTS[os_key], _CPU_CONSTRAINTS[cpu]],
            "# Host fallback: no prebuilt git is published for %s." % host,
        ))
    return "\n".join(lines)

def host_toolchain_lines(toolchain_type_label, exec_constraints, comment):
    """Render a toolchain over the repo's `host/git` (a symlink to the host's git).

    Args:
        toolchain_type_label: Canonical label string for //git:toolchain_type.
        exec_constraints: Constraint labels the toolchain is restricted to.
        comment: Comment line placed above the targets.

    Returns:
        BUILD file lines declaring `:host_git`, `:host_impl` and `:host`.
    """
    return [
        comment,
        "filegroup(",
        "    name = \"host_git\",",
        "    srcs = [\"host/git\"],",
        ")",
        "",
        "git_toolchain(",
        "    name = \"host_impl\",",
        "    git = \":host_git\",",
        ")",
        "",
        "toolchain(",
        "    name = \"host\",",
        "    toolchain = \":host_impl\",",
        "    toolchain_type = \"%s\"," % toolchain_type_label,
        "    exec_compatible_with = [",
    ] + [
        "        \"%s\"," % constraint
        for constraint in exec_constraints
    ] + [
        "    ],",
        ")",
        "",
    ]

def render_host_git_build(defs_label, toolchain_type_label, exec_constraints, comment):
    """Render a standalone BUILD file with only a host git toolchain (see `host_toolchain_lines`).

    Args:
        defs_label: Canonical label string for //git:defs.bzl.
        toolchain_type_label: Canonical label string for //git:toolchain_type.
        exec_constraints: Constraint labels the toolchain is restricted to.
        comment: Comment line placed above the targets.

    Returns:
        BUILD file content.
    """
    return "\n".join([
        "load(\"%s\", \"git_toolchain\")" % defs_label,
        "",
    ] + host_toolchain_lines(toolchain_type_label, exec_constraints, comment))

def link_host_git(ctx):
    """Symlink the host's `git` from PATH to `host/git` in the repo, tracking PATH.

    Args:
        ctx: Repository context.

    Returns:
        True if a host git was found and linked, else False.
    """

    # `which` does not register PATH as an input; read it so a different git on PATH
    # re-evaluates the repo.
    ctx.getenv("PATH")
    host_git = ctx.which("git")
    if not host_git:
        return False
    ctx.symlink(host_git, "host/git")
    return True

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
    platform_repos = {
        "linux-aarch64": _repo_name(ctx.attr.linux_aarch64) if ctx.attr.linux_aarch64 else None,
        "linux-x86_64": _repo_name(ctx.attr.linux_x86_64) if ctx.attr.linux_x86_64 else None,
    }

    # On a host platform that never has a prebuilt (macOS), fall back to the host's git so
    # consumers that require the toolchain type still resolve. A prebuilt disabled with
    # `setup(<platform>_sha256 = "")` does not qualify: that keeps the source fallback, and a
    # Linux-constrained host toolchain could be selected for remote Linux workers.
    host = None
    if ctx.attr.host_fallback:
        host = host_fallback_platform(host_platform(ctx.os.name, ctx.os.arch))
    if host and not link_host_git(ctx):
        host = None

    ctx.file("BUILD.bazel", render_git_toolchains_build(
        platform_repos,
        ctx.attr.defs_label,
        ctx.attr.toolchain_type_label,
        host = host,
    ))

    # The host fallback depends on PATH, so only the prebuilt-only hub is reproducible.
    return ctx.repo_metadata(reproducible = host == None)

git_toolchains_hub = repository_rule(
    implementation = _git_toolchains_hub_impl,
    attrs = {
        "defs_label": attr.string(mandatory = True),
        "host_fallback": attr.bool(default = True),
        "linux_aarch64": attr.label(default = None),
        "linux_x86_64": attr.label(default = None),
        "toolchain_type_label": attr.string(mandatory = True),
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
