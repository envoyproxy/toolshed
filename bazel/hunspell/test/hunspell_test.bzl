"""Tests for the resolved hunspell toolchain and the prebuilt hub rendering."""

load("@bazel_skylib//lib:unittest.bzl", "asserts", "unittest")
load("//hunspell:defs.bzl", "HUNSPELL_TOOLCHAIN_TYPE")
load("//hunspell/private:hunspell_prebuilt.bzl", "render_hunspell_toolchains_build")

_SCRIPT = """#!/usr/bin/env bash
set -euo pipefail
runfiles="${TEST_SRCDIR:-$0.runfiles}"
exec "$runfiles/@@CHECK@@" "$runfiles/@@HUNSPELL@@" "$runfiles/@@DICT@@"
"""

def _runfile_path(ctx, file):
    if file.short_path.startswith("../"):
        return file.short_path[3:]
    return "%s/%s" % (ctx.workspace_name, file.short_path)

def _hunspell_toolchain_test_impl(ctx):
    info = ctx.toolchains[HUNSPELL_TOOLCHAIN_TYPE].hunspell
    script = ctx.actions.declare_file(ctx.label.name + ".sh")
    ctx.actions.write(
        script,
        _SCRIPT
            .replace("@@CHECK@@", _runfile_path(ctx, ctx.file.check))
            .replace("@@HUNSPELL@@", _runfile_path(ctx, info.hunspell))
            .replace("@@DICT@@", _runfile_path(ctx, info.dictionary)[:-len(".dic")]),
        is_executable = True,
    )
    runfiles = info.runfiles.merge(ctx.runfiles(files = [ctx.file.check]))
    return [DefaultInfo(executable = script, runfiles = runfiles)]

hunspell_toolchain_test = rule(
    implementation = _hunspell_toolchain_test_impl,
    attrs = {
        "check": attr.label(allow_single_file = True, mandatory = True),
    },
    test = True,
    toolchains = [HUNSPELL_TOOLCHAIN_TYPE],
)

_DEFS = "@" + "@envoy_toolshed+//hunspell:defs.bzl"
_TOOLCHAIN_TYPE = "@" + "@envoy_toolshed+//hunspell:toolchain_type"

def _render(platform_repos):
    return render_hunspell_toolchains_build(platform_repos, _DEFS, _TOOLCHAIN_TYPE)

def _assert_platform(env, content, name, repo, cpu):
    asserts.true(env, "name = \"%s_impl\"" % name in content)
    asserts.true(env, "toolchain = \":%s_impl\"" % name in content)
    for path in ["share/hunspell/en_US.aff", "share/hunspell/en_US.dic", "hunspell"]:
        asserts.true(env, ("\"@" + "@%s//:%s\"") % (repo, path) in content)
    asserts.true(env, "\"@platforms//cpu:%s\"" % cpu in content)

def _render_hub_build_test_impl(ctx):
    env = unittest.begin(ctx)

    content = _render({
        "linux-aarch64": "hunspell_prebuilt_linux_aarch64",
        "linux-x86_64": "hunspell_prebuilt_linux_x86_64",
    })
    asserts.true(env, ("load(\"%s\", \"hunspell_toolchain\")" % _DEFS) in content)
    asserts.equals(env, 2, content.count("toolchain_type = \"%s\"" % _TOOLCHAIN_TYPE))
    asserts.equals(env, 2, content.count("\"@platforms//os:linux\""))
    _assert_platform(env, content, "linux_aarch64", "hunspell_prebuilt_linux_aarch64", "aarch64")
    _assert_platform(env, content, "linux_x86_64", "hunspell_prebuilt_linux_x86_64", "x86_64")

    content = _render({"linux-aarch64": None, "linux-x86_64": "hunspell_prebuilt_linux_x86_64"})
    _assert_platform(env, content, "linux_x86_64", "hunspell_prebuilt_linux_x86_64", "x86_64")
    asserts.false(env, "linux_aarch64" in content)
    asserts.false(env, "@platforms//cpu:aarch64" in content)

    content = _render({"linux-aarch64": "hunspell_prebuilt_linux_aarch64", "linux-x86_64": None})
    _assert_platform(env, content, "linux_aarch64", "hunspell_prebuilt_linux_aarch64", "aarch64")
    asserts.false(env, "linux_x86_64" in content)
    asserts.false(env, "@platforms//cpu:x86_64" in content)

    # Both disabled (the default until a bins release publishes hashes): an empty hub, so only
    # the consumer's own toolchains can match.
    content = _render({"linux-aarch64": None, "linux-x86_64": None})
    asserts.false(env, "hunspell_toolchain(" in content)
    asserts.false(env, "toolchain(" in content)
    return unittest.end(env)

render_hub_build_test = unittest.make(_render_hub_build_test_impl)
