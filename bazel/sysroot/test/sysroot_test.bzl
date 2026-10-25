"""Regression tests for directory sysroots and their file-level targets."""

load("@bazel_skylib//lib:unittest.bzl", "analysistest", "asserts", "unittest")
load("//:versions.bzl", "VERSIONS")

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

def _sysroot_hashes_test_impl(ctx):
    env = unittest.begin(ctx)
    asserts.equals(env, "0.2.27", VERSIONS["sysroot_stdcc_release"])
    hashes = VERSIONS["sysroot_hashes"]
    published = {
        "2.28": {
            "amd64": "b0a230b3875f36dc50739fb4711e8745a0b65fd1b1e4d0c4961c6832980c0510",
            "arm64": "8fd6257c1a6ea3048d03d46e3a452873f885fd17ced5640deb3b3994c8dda4bf",
        },
        "2.31": {
            "amd64": "0562bde13b68aa1c49ab286c5bb765158a9f17fb69f3f1d190672ef171502dbf",
            "arm64": "db9c5b96cd4ecc9b5ec4ac865d5e91eacf2020ef583aa262c6a906741f46ca11",
        },
    }
    for glibc_version, variants in hashes.items():
        asserts.equals(env, ["13", "base"], sorted(variants.keys()))
        asserts.equals(env, published[glibc_version], variants["13"])
        for arch in ["amd64", "arm64"]:
            asserts.equals(env, 64, len(variants["base"][arch]))
    return unittest.end(env)

sysroot_hashes_test = unittest.make(_sysroot_hashes_test_impl)

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
            if ctx.attr.stdcc_version:
                include_prefix = root.path + "/usr/include/c++/" + ctx.attr.stdcc_version + "/"
                asserts.true(env, any([file.path.startswith(include_prefix) for file in headers]))
                asserts.true(env, any([file.basename.startswith("libstdc++.") for file in libs]))
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
        "stdcc_version": attr.string(),
    },
)
