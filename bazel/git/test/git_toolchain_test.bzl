"""Tests for git toolchain resolution and extension rendering."""

load("@bazel_skylib//lib:unittest.bzl", "analysistest", "asserts", "unittest")
load("//git:defs.bzl", "GIT_TOOLCHAIN_TYPE")
load("//git/private:git_prebuilt.bzl", "render_git_toolchains_build")
load("//git/private:git_source_hub.bzl", "render_git_source_build", "render_git_source_defs", "render_git_source_transitions")

_SOURCE_TOOLCHAIN = str(Label("@envoy_toolshed_git_source//:source_toolchain"))

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

def _render_source_hub_files_test_impl(ctx):
    env = unittest.begin(ctx)
    transitions = render_git_source_transitions("@" + "@curl+//:ssl_lib")
    asserts.true(env, "\"@" + "@curl+//:ssl_lib\"" in transitions)
    defs = render_git_source_defs(
        git_package_bzl_label = "@" + "@envoy_toolshed+//git/private:git_package.bzl",
        git_source_bzl_label = "@" + "@envoy_toolshed+//git/private:git_source.bzl",
    )
    asserts.true(env, "git_files = git_files_rule(" in defs)
    asserts.true(env, "git_source_wrapper = git_source_wrapper_rule(openssl_transition)" in defs)
    build = render_git_source_build(
        cacert_label = "@" + "@cacert+//file",
        gcc_build_label = "@" + "@envoy_toolshed+//compile:gcc_build",
        git_label = "@" + "@git+//:git",
        git_package_bzl_label = "@" + "@envoy_toolshed+//git/private:git_package.bzl",
        git_remote_http_label = "@" + "@git+//:git-remote-http",
        stripper_label = "@" + "@envoy_toolshed+//compile:llvm_minimal_host_llvm_strip",
        templates_label = "@" + "@git+//:templates",
        toolchain_bzl_label = "@" + "@envoy_toolshed+//git:toolchain.bzl",
        toolchain_type_label = "@" + "@envoy_toolshed+//git:toolchain_type",
    )
    asserts.true(env, "name = \"source_toolchain\"" in build)
    asserts.true(env, "load(\":defs.bzl\", \"git_files\", \"git_source_wrapper\")" in build)
    asserts.true(env, "toolchain_type = \"@" + "@envoy_toolshed+//git:toolchain_type\"" in build)
    asserts.true(env, "git = \"@" + "@git+//:git\"" in build)
    return unittest.end(env)

render_source_hub_files_test = unittest.make(_render_source_hub_files_test_impl)
