"""Test-only repository exercising the hub's host git fallback on the current host.

The hub only renders the fallback on hosts without a prebuilt (macOS, Linux on eg ppc64le),
not on CI's Linux x86_64/aarch64, so this repo links the host's git exactly as
the hub does (`link_host_git`) and renders the same targets (`render_host_git_build`), but
constrained to the actual host platform, so the mechanism can be tested on Linux CI by
forcing the toolchain with `--extra_toolchains`.
"""

load(
    "//git/private:git_prebuilt.bzl",
    "host_exec_constraints",
    "host_platform",
    "link_host_git",
    "render_host_git_build",
)

def _git_host_test_impl(ctx):
    host = host_platform(ctx.os.name, ctx.os.arch)
    exec_constraints = host_exec_constraints(host) if host else None
    if not exec_constraints:
        fail("unsupported host %s/%s" % (ctx.os.name, ctx.os.arch))
    if not link_host_git(ctx):
        fail("git not found on PATH")
    ctx.file("BUILD.bazel", render_host_git_build(
        str(Label("//git:defs.bzl")),
        str(Label("//git:toolchain_type")),
        exec_constraints,
        "# Test-only host git toolchain for %s." % host,
    ))

git_host_test = repository_rule(
    implementation = _git_host_test_impl,
    doc = "Test-only repo with a toolchain over the host's git, constrained to this host.",
)
