"""Tests for git toolchain resolution and extension rendering."""

load("@bazel_skylib//lib:unittest.bzl", "analysistest", "asserts", "unittest")
load("//git:defs.bzl", "GIT_TOOLCHAIN_TYPE")
load("//git/private:git_prebuilt.bzl", "render_git_toolchains_build")

_SOURCE_TOOLCHAIN = str(Label("//git:source_toolchain"))

def _repo_marker_name(name, repo_name):
    return "%s_%s.repo_name" % (name, repo_name)

def _git_toolchain_probe_impl(ctx):
    git_info = ctx.toolchains[GIT_TOOLCHAIN_TYPE].git
    repo_name = git_info.git.owner.repo_name
    marker = ctx.actions.declare_file(_repo_marker_name(ctx.label.name, repo_name))
    ctx.actions.write(marker, repo_name + "\n")
    return [
        DefaultInfo(
            executable = git_info.git,
            files = depset([git_info.git, marker]),
            runfiles = git_info.runfiles.merge(ctx.runfiles(files = [marker])),
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
    return [
        DefaultInfo(
            executable = default.files_to_run.executable,
            files = default.files,
            runfiles = default.default_runfiles,
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
        repo_files[0].basename == _repo_marker_name(ctx.attr.target_under_test.label.name, ctx.attr.expected_repo_name),
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
    asserts.true(
        env,
        ("_" + ctx.attr.expected_repo_prefix + ".repo_name") in repo_files[0].basename,
        "expected repo marker prefix %s, got %s" % (ctx.attr.expected_repo_prefix, repo_files[0].basename),
    )
    return analysistest.end(env)

source_repo_test = analysistest.make(
    _source_repo_test_impl,
    attrs = {
        "expected_repo_prefix": attr.string(mandatory = True),
    },
)

def _render_hub_build_test_impl(ctx):
    env = unittest.begin(ctx)
    content = render_git_toolchains_build({
        "linux-aarch64": None,
        "linux-x86_64": "git_prebuilt_linux_x86_64",
    })
    asserts.true(env, "name = \"linux_x86_64\"" in content)
    asserts.false(env, "name = \"linux_aarch64\"" in content)
    asserts.true(env, "@git_prebuilt_linux_x86_64//:git" in content)
    return unittest.end(env)

render_hub_build_test = unittest.make(_render_hub_build_test_impl)
