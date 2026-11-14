"""Tests for the prebuilt pigz hub rendering and the unavailable fallback."""

load("@bazel_skylib//lib:unittest.bzl", "analysistest", "asserts", "unittest")
load("//pigz:toolchain.bzl", "UNAVAILABLE_MESSAGE")
load("//pigz/private:pigz_prebuilt.bzl", "render_pigz_toolchains_build")

_DEFS = "@" + "@envoy_toolshed+//pigz:defs.bzl"
_TOOLCHAIN_TYPE = "@" + "@envoy_toolshed+//pigz:toolchain_type"

def _render(platform_repos):
    return render_pigz_toolchains_build(platform_repos, _DEFS, _TOOLCHAIN_TYPE)

def _assert_platform(env, content, name, repo, cpu):
    asserts.true(env, "name = \"%s_impl\"" % name in content)
    asserts.true(env, "toolchain = \":%s_impl\"" % name in content)
    asserts.true(env, ("pigz = \"@" + "@%s//:pigz\"") % repo in content)
    asserts.true(env, "\"@platforms//cpu:%s\"" % cpu in content)

def _render_hub_build_test_impl(ctx):
    env = unittest.begin(ctx)

    content = _render({
        "linux-aarch64": "pigz_prebuilt_linux_aarch64",
        "linux-x86_64": "pigz_prebuilt_linux_x86_64",
    })
    asserts.true(env, ("load(\"%s\", \"pigz_toolchain\")" % _DEFS) in content)
    asserts.equals(env, 2, content.count("toolchain_type = \"%s\"" % _TOOLCHAIN_TYPE))
    asserts.equals(env, 2, content.count("\"@platforms//os:linux\""))

    # Matched on the platform the binary runs on, not the exec platform of the resolving target.
    asserts.equals(env, 2, content.count("target_compatible_with = ["))
    asserts.false(env, "exec_compatible_with" in content)
    _assert_platform(env, content, "linux_aarch64", "pigz_prebuilt_linux_aarch64", "aarch64")
    _assert_platform(env, content, "linux_x86_64", "pigz_prebuilt_linux_x86_64", "x86_64")

    content = _render({"linux-aarch64": None, "linux-x86_64": "pigz_prebuilt_linux_x86_64"})
    _assert_platform(env, content, "linux_x86_64", "pigz_prebuilt_linux_x86_64", "x86_64")
    asserts.false(env, "linux_aarch64" in content)
    asserts.false(env, "@platforms//cpu:aarch64" in content)

    content = _render({"linux-aarch64": "pigz_prebuilt_linux_aarch64", "linux-x86_64": None})
    _assert_platform(env, content, "linux_aarch64", "pigz_prebuilt_linux_aarch64", "aarch64")
    asserts.false(env, "linux_x86_64" in content)
    asserts.false(env, "@platforms//cpu:x86_64" in content)

    # Both disabled (the default until a bins release publishes hashes): an empty hub, so only
    # the source fallback can match.
    content = _render({"linux-aarch64": None, "linux-x86_64": None})
    asserts.false(env, "pigz_toolchain(" in content)
    asserts.false(env, "toolchain(" in content)
    return unittest.end(env)

render_hub_build_test = unittest.make(_render_hub_build_test_impl)

def _unavailable_test_impl(ctx):
    env = analysistest.begin(ctx)
    asserts.expect_failure(env, UNAVAILABLE_MESSAGE)
    return analysistest.end(env)

# Resolves `//pigz` for a platform with no pigz toolchain other than the unavailable fallback.
unavailable_test = analysistest.make(
    _unavailable_test_impl,
    expect_failure = True,
    config_settings = {
        "//command_line_option:platforms": str(Label("//pigz/test:no_pigz_platform")),
    },
)
