"""Repository rule exposing a host-arch prebuilt `sq` binary as `@sq//:sq`."""

SQ_REPO_BUILD = """exports_files(["bin/sq"])
filegroup(name = "sq", srcs = ["bin/sq"], visibility = ["//visibility:public"])
"""

def _normalize_sq_repo_os(os_name):
    os_name = os_name.lower()
    if os_name.startswith("linux"):
        return "linux"
    return None

def _normalize_sq_repo_arch(arch):
    arch = arch.lower()
    if arch.startswith("x86_64") or arch.startswith("amd64"):
        return "x86_64"
    if arch.startswith("aarch64") or arch.startswith("arm64"):
        return "aarch64"
    return None

def _select_sq_repo_root(ctx):
    os_name = _normalize_sq_repo_os(ctx.os.name)
    arch = _normalize_sq_repo_arch(ctx.os.arch)
    if os_name == "linux":
        if arch == "x86_64":
            return ctx.path(ctx.attr.linux_x86_64_build).dirname
        if arch == "aarch64":
            return ctx.path(ctx.attr.linux_arm64_build).dirname
    fail("Unsupported host platform for sq alias: {} {}. Supported combinations are linux/x86_64 and linux/aarch64.".format(ctx.os.name, ctx.os.arch))

def _sq_repo_impl(ctx):
    root = _select_sq_repo_root(ctx)
    result = ctx.execute(["mkdir", "-p", "bin"])
    if result.return_code:
        fail("Failed to create sq alias repo bin directory: {}".format(result.stderr))
    ctx.symlink(root.get_child("bin").get_child("sq"), "bin/sq")
    ctx.file("BUILD.bazel", SQ_REPO_BUILD)

sq_repository = repository_rule(
    implementation = _sq_repo_impl,
    attrs = {
        "linux_arm64_build": attr.label(
            mandatory = True,
            doc = "BUILD.bazel label of the Linux-ARM64 prebuilt sq archive.",
        ),
        "linux_x86_64_build": attr.label(
            mandatory = True,
            doc = "BUILD.bazel label of the Linux-X64 prebuilt sq archive.",
        ),
    },
    doc = "Creates the host-arch @sq repository backed by prebuilt sq archives.",
)
