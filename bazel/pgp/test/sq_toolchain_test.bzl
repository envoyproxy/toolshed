"""Tests for sq toolchain resolution and extension rendering."""

load("@bazel_skylib//lib:unittest.bzl", "analysistest", "asserts", "unittest")
load("//pgp:defs.bzl", "PGP_TOOLCHAIN_TYPE")
load("//pgp/private:sq_prebuilt.bzl", "render_sq_toolchains_build")

_SOURCE_TOOLCHAIN = str(Label("//pgp/dev:sq_toolchain"))

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
mapfile -t matches < <(find "$runfiles" -type f -path '*/bin/sq' | sort)
if [[ "${{#matches[@]}}" -ne 1 ]]; then
    echo "expected exactly one sq binary in runfiles, got ${{#matches[@]}}" >&2
    printf 'matches:\\n%s\\n' "${{matches[*]:-}}" >&2
    exit 1
fi
exec "${{matches[0]}}" "$@"
"""

def _repo_marker_name(name, repo_name):
    return "%s_%s.repo_name" % (name, repo_name)

def _runfile_path(ctx, file):
    if file.short_path.startswith("../"):
        return file.short_path[3:]
    return "%s/%s" % (ctx.workspace_name, file.short_path)

def _declare_launcher(ctx):
    launcher = ctx.actions.declare_file(ctx.label.name + ".sh")
    ctx.actions.write(
        launcher,
        _LAUNCHER_TEMPLATE.format(launcher = _runfile_path(ctx, launcher)),
        is_executable = True,
    )
    return launcher

def _sq_toolchain_probe_impl(ctx):
    signer_info = ctx.toolchains[PGP_TOOLCHAIN_TYPE].pgp_signer
    repo_name = signer_info.signer.owner.repo_name
    marker = ctx.actions.declare_file(_repo_marker_name(ctx.label.name, repo_name))
    ctx.actions.write(marker, repo_name + "\n")
    launcher = _declare_launcher(ctx)
    return [
        DefaultInfo(
            executable = launcher,
            files = depset([launcher, marker]),
            runfiles = signer_info.runfiles.merge(ctx.runfiles(files = [marker])),
        ),
        OutputGroupInfo(repo_name = depset([marker])),
    ]

sq_toolchain_probe = rule(
    implementation = _sq_toolchain_probe_impl,
    executable = True,
    toolchains = [PGP_TOOLCHAIN_TYPE],
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
    return analysistest.end(env)

source_repo_test = analysistest.make(
    _source_repo_test_impl,
    attrs = {
        "forbidden_repo_substring": attr.string(mandatory = True),
    },
)

def _render_hub_build_test_impl(ctx):
    env = unittest.begin(ctx)
    content = render_sq_toolchains_build(
        {
            "Linux-ARM64": None,
            "Linux-X64": "sq_prebuilt_linux_x86_64",
        },
        "@" + "@envoy_toolshed+//pgp:defs.bzl",
        "@" + "@envoy_toolshed+//pgp:toolchain_type",
    )
    asserts.true(env, "name = \"linux_x86_64\"" in content)
    asserts.false(env, "name = \"linux_aarch64\"" in content)
    asserts.true(env, "load(\"@" + "@envoy_toolshed+//pgp:defs.bzl\", \"pgp_toolchain\", \"sq_signer\")" in content)
    asserts.true(env, "toolchain_type = \"@" + "@envoy_toolshed+//pgp:toolchain_type\"" in content)
    asserts.true(env, "@" + "@sq_prebuilt_linux_x86_64//:sq" in content)
    return unittest.end(env)

render_hub_build_test = unittest.make(_render_hub_build_test_impl)
