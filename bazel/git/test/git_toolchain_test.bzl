"""Tests for git toolchain resolution and extension rendering."""

load("@bazel_skylib//lib:unittest.bzl", "analysistest", "asserts", "unittest")
load("//git:defs.bzl", "GIT_TOOLCHAIN_TYPE")
load("//git/private:git_prebuilt.bzl", "render_git_toolchains_build")

_SOURCE_TOOLCHAIN = str(Label("//git/dev:source_toolchain"))

_LAUNCHER_TEMPLATE = """#!/bin/bash
set -euo pipefail
self="$0"
case "$self" in
    /*) ;;
    *) self="$(pwd)/$self" ;;
esac
if [[ -n "${{RUNFILES_DIR:-}}" ]]; then
    runfiles="$RUNFILES_DIR"
elif [[ -n "${{TEST_SRCDIR:-}}" ]]; then
    runfiles="$TEST_SRCDIR"
elif [[ -d "$self.runfiles" ]]; then
    runfiles="$self.runfiles"
else
    launcher="/{launcher}"
    case "$self" in
        *"$launcher") runfiles="${{self%"$launcher"}}" ;;
        *) runfiles="$(CDPATH= cd "$(dirname "$self")" && pwd)" ;;
    esac
fi
exec "$runfiles/{git}" "$@"
"""

def _repo_marker_name(name, repo_name):
    return "%s_%s.repo_name" % (name, repo_name)

def _runfile_path(ctx, executable):
    if executable.short_path.startswith("../"):
        return executable.short_path[3:]
    return "%s/%s" % (ctx.workspace_name, executable.short_path)

def _declare_launcher(ctx, executable):
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

def _git_toolchain_probe_impl(ctx):
    git_info = ctx.toolchains[GIT_TOOLCHAIN_TYPE].git
    repo_name = git_info.git.owner.repo_name
    marker = ctx.actions.declare_file(_repo_marker_name(ctx.label.name, repo_name))
    ctx.actions.write(marker, repo_name + "\n")
    launcher = _declare_launcher(ctx, git_info.git)
    return [
        DefaultInfo(
            executable = launcher,
            files = depset([launcher, marker]),
            runfiles = git_info.runfiles.merge(ctx.runfiles(files = [git_info.git, marker])),
        ),
        OutputGroupInfo(repo_name = depset([marker])),
    ]

git_toolchain_probe = rule(
    implementation = _git_toolchain_probe_impl,
    executable = True,
    toolchains = [GIT_TOOLCHAIN_TYPE],
)

def _source_toolchain_transition_impl(_settings, _attr):
    return {"//command_line_option:extra_toolchains": [_SOURCE_TOOLCHAIN]}

_source_toolchain_transition = transition(
    implementation = _source_toolchain_transition_impl,
    inputs = [],
    outputs = ["//command_line_option:extra_toolchains"],
)

def _source_probe_impl(ctx):
    default = ctx.attr.probe[0][DefaultInfo]
    launcher = _declare_launcher(ctx, default.files_to_run.executable)
    return [
        DefaultInfo(
            executable = launcher,
            files = depset([launcher]),
            runfiles = default.default_runfiles.merge(ctx.runfiles(files = default.files.to_list())),
        ),
        OutputGroupInfo(repo_name = ctx.attr.probe[0][OutputGroupInfo].repo_name),
    ]

source_toolchain_probe = rule(
    implementation = _source_probe_impl,
    executable = True,
    attrs = {
        "probe": attr.label(
            mandatory = True,
            executable = True,
            cfg = _source_toolchain_transition,
        ),
        "_allowlist_function_transition": attr.label(
            default = "@bazel_tools//tools/allowlists/function_transition_allowlist",
        ),
    },
)

def _resolved_repo_test_impl(ctx):
    env = analysistest.begin(ctx)
    repo_files = analysistest.target_under_test(env)[OutputGroupInfo].repo_name.to_list()
    asserts.equals(env, 1, len(repo_files))
    asserts.true(
        env,
        ctx.attr.expected_repo_name in repo_files[0].basename and repo_files[0].basename.endswith(".repo_name"),
        "expected repo marker for %s, got %s" % (ctx.attr.expected_repo_name, repo_files[0].basename),
    )
    return analysistest.end(env)

resolved_repo_test = analysistest.make(
    _resolved_repo_test_impl,
    attrs = {
        "expected_repo_name": attr.string(mandatory = True),
    },
)

def _source_repo_test_impl(ctx):
    env = analysistest.begin(ctx)
    repo_files = analysistest.target_under_test(env)[OutputGroupInfo].repo_name.to_list()
    asserts.equals(env, 1, len(repo_files))
    basename = repo_files[0].basename
    asserts.false(
        env,
        ctx.attr.forbidden_repo_substring in basename,
        "unexpected repo marker substring %s in %s" % (ctx.attr.forbidden_repo_substring, basename),
    )
    if ctx.attr.expected_repo_substring:
        asserts.true(
            env,
            ctx.attr.expected_repo_substring in basename,
            "expected repo marker substring %s, got %s" % (ctx.attr.expected_repo_substring, basename),
        )
    return analysistest.end(env)

source_repo_test = analysistest.make(
    _source_repo_test_impl,
    attrs = {
        "expected_repo_substring": attr.string(default = ""),
        "forbidden_repo_substring": attr.string(mandatory = True),
    },
)

def _render_hub_build_test_impl(ctx):
    env = unittest.begin(ctx)
    content = render_git_toolchains_build(
        {
            "linux-aarch64": None,
            "linux-x86_64": "git_prebuilt_linux_x86_64",
        },
        "@" + "@envoy_toolshed+//git:defs.bzl",
        "@" + "@envoy_toolshed+//git:toolchain_type",
    )
    asserts.true(env, "name = \"linux_x86_64\"" in content)
    asserts.false(env, "name = \"linux_aarch64\"" in content)
    asserts.true(env, "load(\"@" + "@envoy_toolshed+//git:defs.bzl\", \"git_toolchain\")" in content)
    asserts.true(env, "toolchain_type = \"@" + "@envoy_toolshed+//git:toolchain_type\"" in content)
    asserts.true(env, "@" + "@git_prebuilt_linux_x86_64//:git" in content)
    return unittest.end(env)

render_hub_build_test = unittest.make(_render_hub_build_test_impl)
