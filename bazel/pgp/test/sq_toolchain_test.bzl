"""Tests for sq toolchain resolution and extension rendering."""

load("@bazel_skylib//lib:unittest.bzl", "analysistest", "asserts", "unittest")
load("//pgp:defs.bzl", "PGP_TOOLCHAIN_TYPE")
load("//pgp/private:sq_prebuilt.bzl", "render_sq_toolchains_build")

_PREBUILT_TOOLCHAINS = str(Label("@sq_toolchains//:all"))
_SOURCE_TOOLCHAIN = str(Label("//pgp/dev:sq_toolchain"))

# Basenames the resolved signer's `sq` executable may have: `bin/sq` in the
# prebuilt tarball, `sq_from_source` for the registry source build.
_SQ_BASENAMES = ["sq", "sq_from_source"]

# Mirrors //git/test: the runfiles path of the resolved `sq` is baked in at
# analysis time rather than discovered with `find` at runtime, which is not
# reliable across sandboxed/remote runfiles layouts.
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
sq="$runfiles/{sq}"
if [[ ! -e "$sq" ]]; then
    echo "sq not found in runfiles: $sq" >&2
    echo "runfiles root: $runfiles" >&2
    find "$runfiles" -maxdepth 3 -print >&2 || true
    exit 1
fi
exec "$sq" "$@"
"""

def _repo_marker_name(name, repo_name):
    return "%s_%s.repo_name" % (name, repo_name)

def _runfile_path(ctx, file):
    if file.short_path.startswith("../"):
        return file.short_path[3:]
    return "%s/%s" % (ctx.workspace_name, file.short_path)

def _find_sq(ctx, signer_info):
    """Locate the `sq` executable in the resolved signer's runfiles."""
    candidates = [
        f
        for f in signer_info.runfiles.files.to_list()
        if f.basename in _SQ_BASENAMES and not f.is_directory
    ]
    if len(candidates) != 1:
        fail("%s: expected exactly one sq executable in the resolved signer's runfiles, got %d: %s" % (
            ctx.label,
            len(candidates),
            [f.short_path for f in candidates],
        ))
    return candidates[0]

def _declare_launcher(ctx, sq):
    launcher = ctx.actions.declare_file(ctx.label.name + ".sh")
    ctx.actions.write(
        launcher,
        _LAUNCHER_TEMPLATE.format(
            launcher = _runfile_path(ctx, launcher),
            sq = _runfile_path(ctx, sq),
        ),
        is_executable = True,
    )
    return launcher

def _sq_toolchain_probe_impl(ctx):
    signer_info = ctx.toolchains[PGP_TOOLCHAIN_TYPE].pgp_signer
    repo_name = signer_info.signer.owner.repo_name
    marker = ctx.actions.declare_file(_repo_marker_name(ctx.label.name, repo_name))
    ctx.actions.write(marker, repo_name + "\n")

    # The stub signer registered for //pgp/test analysis tests has no `sq`;
    # only bake a real launcher when one is present so the default-resolution
    # probe (`:resolved_sq`) still analyses under the stub.
    sq_files = [
        f
        for f in signer_info.runfiles.files.to_list()
        if f.basename in _SQ_BASENAMES and not f.is_directory
    ]
    if sq_files:
        launcher = _declare_launcher(ctx, _find_sq(ctx, signer_info))
    else:
        launcher = ctx.actions.declare_file(ctx.label.name + ".sh")
        ctx.actions.write(
            launcher,
            "#!/bin/bash\necho 'resolved signer (%s) does not bundle sq' >&2\nexit 1\n" % signer_info.signer.short_path,
            is_executable = True,
        )
    return [
        DefaultInfo(
            executable = launcher,
            files = depset([launcher, marker]),
            runfiles = signer_info.runfiles.merge(ctx.runfiles(files = [marker] + sq_files)),
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

def _prebuilt_toolchain_transition_impl(_settings, _attr):
    return {"//command_line_option:extra_toolchains": [_PREBUILT_TOOLCHAINS]}

_prebuilt_toolchain_transition = transition(
    implementation = _prebuilt_toolchain_transition_impl,
    inputs = [],
    outputs = ["//command_line_option:extra_toolchains"],
)

def _source_probe_impl(ctx):
    probe = ctx.attr.probe[0]
    default = probe[DefaultInfo]
    inner = default.files_to_run.executable

    # An executable rule must own the executable it returns, so wrap the
    # transitioned inner probe's launcher in a symlink declared here. The inner
    # launcher has the sq runfiles path baked in, so no path rewriting is
    # needed; its own files (launcher + repo_name marker) are carried along in
    # runfiles.
    launcher = ctx.actions.declare_file(ctx.label.name + ".sh")
    ctx.actions.symlink(output = launcher, target_file = inner, is_executable = True)
    return [
        DefaultInfo(
            executable = launcher,
            files = depset([launcher]),
            runfiles = default.default_runfiles.merge(ctx.runfiles(files = default.files.to_list())),
        ),
        OutputGroupInfo(repo_name = probe[OutputGroupInfo].repo_name),
    ]

def _probe_attrs(cfg):
    return {
        "probe": attr.label(
            mandatory = True,
            executable = True,
            cfg = cfg,
        ),
        "_allowlist_function_transition": attr.label(
            default = "@bazel_tools//tools/allowlists/function_transition_allowlist",
        ),
    }

prebuilt_toolchain_probe = rule(
    implementation = _source_probe_impl,
    executable = True,
    attrs = _probe_attrs(_prebuilt_toolchain_transition),
)

source_toolchain_probe = rule(
    implementation = _source_probe_impl,
    executable = True,
    attrs = _probe_attrs(_source_toolchain_transition),
)

def _resolved_repo_test_impl(ctx):
    env = analysistest.begin(ctx)
    repo_files = analysistest.target_under_test(env)[OutputGroupInfo].repo_name.to_list()
    asserts.equals(env, 1, len(repo_files))
    basename = repo_files[0].basename
    if ctx.attr.expect_main_repo:
        asserts.true(
            env,
            basename.endswith("_.repo_name"),
            "expected main-repo marker, got %s" % basename,
        )
    else:
        asserts.true(
            env,
            ctx.attr.expected_repo_name in basename and basename.endswith(".repo_name"),
            "expected repo marker for %s, got %s" % (ctx.attr.expected_repo_name, basename),
        )
    return analysistest.end(env)

resolved_repo_test = analysistest.make(
    _resolved_repo_test_impl,
    attrs = {
        "expect_main_repo": attr.bool(default = False),
        "expected_repo_name": attr.string(default = ""),
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
    if ctx.attr.expect_main_repo:
        asserts.true(
            env,
            basename.endswith("_.repo_name"),
            "expected main-repo marker, got %s" % basename,
        )
    return analysistest.end(env)

source_repo_test = analysistest.make(
    _source_repo_test_impl,
    attrs = {
        "expect_main_repo": attr.bool(default = False),
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
