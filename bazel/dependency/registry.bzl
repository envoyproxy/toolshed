"""Rules for resolving, checking, and rewriting Bazel registry pins."""

load("@bazel_skylib//rules:common_settings.bzl", "BuildSettingInfo")
load("//git:defs.bzl", "GIT_TOOLCHAIN_TYPE")

REGISTRY_RESOLVE_EXECUTION_REQUIREMENTS = {
    "local": "1",
    "no-cache": "1",
    "no-remote": "1",
    "requires-network": "1",
}

REGISTRY_RESOLVE_MNEMONIC = "RegistryResolve"
REGISTRY_RESOLVE_TOOLCHAINS = [GIT_TOOLCHAIN_TYPE]

_LAUNCHER_TEMPLATE = """#!/bin/bash
set -euo pipefail
self="$0"
case "$self" in
    /*) ;;
    *) self="$(pwd)/$self" ;;
esac
if [[ -n "${RUNFILES_DIR:-}" ]]; then
    runfiles="$RUNFILES_DIR"
elif [[ -n "${TEST_SRCDIR:-}" ]]; then
    runfiles="$TEST_SRCDIR"
elif [[ -d "$self.runfiles" ]]; then
    runfiles="$self.runfiles"
else
    launcher="/{launcher}"
    case "$self" in
        *"$launcher") runfiles="${self%"$launcher"}" ;;
        *) runfiles="$(CDPATH= cd "$(dirname "$self")" && pwd)" ;;
    esac
fi
exec "$runfiles/{git}" "$@"
"""


def _runfile_path(ctx, file_):
    if file_.short_path.startswith("../"):
        return file_.short_path[3:]
    return "%s/%s" % (ctx.workspace_name, file_.short_path)


def _tool_runfiles(target):
    default = target[DefaultInfo]
    return default.default_runfiles.files if default.default_runfiles else depset()


def _declare_git_launcher(ctx, executable):
    launcher = ctx.actions.declare_file(ctx.label.name + ".sh")
    ctx.actions.write(
        launcher,
        _LAUNCHER_TEMPLATE.format(
            git = _runfile_path(ctx, executable),
            launcher = _runfile_path(ctx, launcher),
        ),
        is_executable = True,
    )
    return launcher


def _git_launcher_impl(ctx):
    git_info = ctx.toolchains[GIT_TOOLCHAIN_TYPE].git
    launcher = _declare_git_launcher(ctx, git_info.git)
    return [
        DefaultInfo(
            executable = launcher,
            files = depset([launcher]),
            runfiles = git_info.runfiles.merge(ctx.runfiles(files = [git_info.git])),
        ),
    ]


git_launcher = rule(
    implementation = _git_launcher_impl,
    executable = True,
    toolchains = [GIT_TOOLCHAIN_TYPE],
)


def _json_string(value):
    return value.replace("\\", "\\\\").replace("\"", "\\\"").replace("\n", "\\n")


def _registry_settings_impl(ctx):
    requested_sha = ctx.attr._sha[BuildSettingInfo].value
    allow_unsafe = "true" if ctx.attr._allow_unsafe[BuildSettingInfo].value else "false"
    output = ctx.actions.declare_file(ctx.label.name + ".json")
    ctx.actions.write(
        output,
        """{
  \"requested_sha\": \"%s\",
  \"allow_unsafe\": %s
}
""" % (_json_string(requested_sha), allow_unsafe),
    )
    return [DefaultInfo(files = depset([output]))]


registry_settings = rule(
    implementation = _registry_settings_impl,
    attrs = {
        "_allow_unsafe": attr.label(default = Label("//dependency:registry_allow_unsafe")),
        "_sha": attr.label(default = Label("//dependency:registry_sha")),
    },
)


def _registry_resolve_impl(ctx):
    git_info = ctx.toolchains[GIT_TOOLCHAIN_TYPE].git
    requested_sha = ctx.attr._sha[BuildSettingInfo].value
    allow_unsafe = ctx.attr._allow_unsafe[BuildSettingInfo].value
    out = ctx.actions.declare_file(ctx.label.name + ".json")

    arguments = [
        "resolve",
        "--repo=%s" % ctx.attr.repo,
        "--url=%s" % ctx.attr.url,
        "--branch=%s" % ctx.attr.branch,
        "--requested-sha=%s" % requested_sha,
        "--allow-unsafe=%s" % ("true" if allow_unsafe else "false"),
        "--json-out=%s" % out.path,
        "--git-bin=%s" % git_info.git.path,
        "--jq-bin=%s" % ctx.executable._jq.path,
        "--jq-root=%s" % ctx.file._jq_root_marker.path,
    ]
    if ctx.attr.release_tags:
        arguments.append("--release-tags=%s" % ctx.attr.release_tags)

    ctx.actions.run(
        executable = ctx.executable._registry_resolve,
        arguments = arguments,
        inputs = depset([ctx.file._jq_root_marker], transitive = [depset(ctx.files._jq_libs)]),
        outputs = [out],
        tools = depset(
            [ctx.executable._jq, git_info.git],
            transitive = [git_info.runfiles.files, _tool_runfiles(ctx.attr._jq)],
        ),
        mnemonic = REGISTRY_RESOLVE_MNEMONIC,
        progress_message = "Resolving %s@%s" % (ctx.attr.repo, ctx.attr.branch),
        execution_requirements = REGISTRY_RESOLVE_EXECUTION_REQUIREMENTS,
    )
    return [DefaultInfo(files = depset([out]))]


registry_resolve = rule(
    implementation = _registry_resolve_impl,
    attrs = {
        "_allow_unsafe": attr.label(default = Label("//dependency:registry_allow_unsafe")),
        "_jq": attr.label(
            allow_single_file = True,
            cfg = "exec",
            default = Label("@jq_toolchains//:resolved_toolchain"),
            executable = True,
        ),
        "_jq_libs": attr.label(
            allow_files = True,
            default = Label("@envoy_toolshed_jq//:modules"),
        ),
        "_jq_root_marker": attr.label(
            allow_single_file = True,
            default = Label("@envoy_toolshed_jq//:modules_root.marker"),
        ),
        "_registry_resolve": attr.label(
            allow_single_file = True,
            cfg = "exec",
            default = Label("//dependency:registry-resolve.sh"),
            executable = True,
        ),
        "_sha": attr.label(default = Label("//dependency:registry_sha")),
        "branch": attr.string(default = "main"),
        "release_tags": attr.string(),
        "repo": attr.string(mandatory = True),
        "url": attr.string(mandatory = True),
    },
    toolchains = REGISTRY_RESOLVE_TOOLCHAINS,
)


def _registry_bazelrc_impl(ctx):
    out = ctx.actions.declare_file(ctx.label.name + "/" + ctx.file.bazelrc.basename)
    ctx.actions.run(
        inputs = [ctx.file.bazelrc, ctx.file.registry],
        outputs = [out],
        arguments = [
            ctx.file.bazelrc.path,
            ctx.file.registry.path,
            ctx.attr.url,
            out.path,
            ctx.executable._jq.path,
        ],
        executable = ctx.executable._registry_bazelrc,
        mnemonic = "RegistryBazelrc",
        tools = depset(
            [ctx.executable._jq],
            transitive = [_tool_runfiles(ctx.attr._jq)],
        ),
    )
    return [DefaultInfo(files = depset([out]))]


registry_bazelrc = rule(
    implementation = _registry_bazelrc_impl,
    attrs = {
        "_jq": attr.label(
            allow_single_file = True,
            cfg = "exec",
            default = Label("@jq_toolchains//:resolved_toolchain"),
            executable = True,
        ),
        "_registry_bazelrc": attr.label(
            allow_single_file = True,
            cfg = "exec",
            default = Label("//dependency:registry_bazelrc.sh"),
            executable = True,
        ),
        "bazelrc": attr.label(mandatory = True, allow_single_file = True),
        "registry": attr.label(mandatory = True, allow_single_file = True),
        "url": attr.string(mandatory = True),
    },
)
