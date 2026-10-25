"""Regression tests for directory sysroots and their file-level targets."""

load("@bazel_skylib//lib:unittest.bzl", "analysistest", "asserts", "unittest")

def _sysroot_build_test_impl(ctx):
    env = analysistest.begin(ctx)
    target = analysistest.target_under_test(env)
    asserts.equals(
        env,
        [
            "sysroot-glibc2.28-amd64.tar.xz",
            "sysroot-glibc2.28-arm64.tar.xz",
            "sysroot-glibc2.31-amd64.tar.xz",
            "sysroot-glibc2.31-arm64.tar.xz",
        ],
        sorted([file.basename for file in target[DefaultInfo].files.to_list()]),
    )
    return analysistest.end(env)

sysroot_build_test = analysistest.make(_sysroot_build_test_impl)

def _sysroot_test_impl(ctx):
    env = unittest.begin(ctx)
    files = ctx.attr.sysroot[DefaultInfo].files.to_list()
    asserts.equals(env, 1, len(files))
    if len(files) == 1:
        root = files[0]
        asserts.equals(env, "sysroot", root.basename)
        if ctx.attr.toolchain_sysroot:
            asserts.equals(env, files, ctx.attr.toolchain_sysroot[DefaultInfo].files.to_list())
        if ctx.attr.headers:
            headers = ctx.attr.headers[DefaultInfo].files.to_list()
            libs = ctx.attr.libs[DefaultInfo].files.to_list()
            asserts.true(env, len(headers) > 0)
            asserts.true(env, len(libs) > 0)
            asserts.true(env, ctx.file.stdio in headers)
            for file in headers + libs:
                asserts.true(env, file.path.startswith(root.path + "/"))
                asserts.false(env, ":" in file.basename or file.basename.endswith(".pl"))
    return unittest.end(env)

sysroot_test = unittest.make(
    _sysroot_test_impl,
    attrs = {
        "sysroot": attr.label(mandatory = True),
        "toolchain_sysroot": attr.label(),
        "headers": attr.label(),
        "libs": attr.label(),
        "stdio": attr.label(allow_single_file = True),
    },
)
