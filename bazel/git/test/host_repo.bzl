"""Test-only repository exercising the hub's host git fallback on the current host.

The hub only renders the fallback for macOS, so this repo links the host's git exactly as
the hub does (`link_host_git`) and renders the same targets (`render_host_git_build`), but
constrained to the actual host platform, so the mechanism can be tested on Linux CI by
forcing the toolchain with `--extra_toolchains`.
"""

load("//git/private:git_prebuilt.bzl", "host_platform", "link_host_git", "render_host_git_build")

_OS_CONSTRAINTS = {
    "linux": "@platforms//os:linux",
    "macos": "@platforms//os:macos",
}

_CPU_CONSTRAINTS = {
    "aarch64": "@platforms//cpu:aarch64",
    "x86_64": "@platforms//cpu:x86_64",
}

def _git_host_test_impl(ctx):
    host = host_platform(ctx.os.name, ctx.os.arch)
    if not host:
        fail("unsupported host %s/%s" % (ctx.os.name, ctx.os.arch))
    os_key, cpu = host.split("-", 1)
    if not link_host_git(ctx):
        fail("git not found on PATH")
    ctx.file("BUILD.bazel", render_host_git_build(
        str(Label("//git:defs.bzl")),
        str(Label("//git:toolchain_type")),
        [_OS_CONSTRAINTS[os_key], _CPU_CONSTRAINTS[cpu]],
        "# Test-only host git toolchain for %s." % host,
    ))

git_host_test = repository_rule(
    implementation = _git_host_test_impl,
    doc = "Test-only repo with a toolchain over the host's git, constrained to this host.",
)
