"""Regression tests for directory sysroots and their file-level targets."""

load("@bazel_skylib//lib:unittest.bzl", "asserts", "unittest")

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
