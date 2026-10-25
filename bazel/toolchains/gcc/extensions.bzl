"""Pinned x86_64-hosted GCC cross compilers using the shared base sysroot."""

load("//:versions.bzl", "VERSIONS")

_GCC = VERSIONS["gcc_toolchain"]

def _gcc_repository_impl(ctx):
    arch = ctx.attr.arch
    triple = arch + "-linux"
    ctx.download_and_extract(
        url = "https://github.com/f0rmiga/gcc-builds/releases/download/{}/gcc-toolchain-{}-{}.tar.xz".format(_GCC["release"], _GCC["version"], arch),
        sha256 = _GCC["sha256"][arch],
    )

    # Never expose the archive's libc to compilation or linking.
    ctx.delete("sysroot")
    prefix = triple + "-" if ctx.path("bin/" + triple + "-as").exists else ""

    # These archives do not ship dwp; never fall back to a host executable.
    ctx.file("xbin/dwp", "#!/bin/bash\necho 'GCC toolchain does not support dwp' >&2\nexit 1\n", executable = True)
    for tool in ["ar", "as", "cpp", "gcc", "gcov", "ld", "nm", "objcopy", "objdump", "readelf", "strip"]:
        binary = "bin/" + prefix + tool
        if not ctx.path(binary).exists:
            fail("GCC archive is missing " + binary)
        ctx.file(
            "xbin/" + tool,
            """#!/bin/bash
set -euo pipefail
ROOT="${PWD}/external/%s"
export PATH="${ROOT}/bin"
unset CPATH C_INCLUDE_PATH CPLUS_INCLUDE_PATH OBJC_INCLUDE_PATH LIBRARY_PATH GCC_EXEC_PREFIX COMPILER_PATH
exec "${ROOT}/%s" "$@"
""" % (ctx.name, binary),
            executable = True,
        )
    cxx_prefix = "aarch64-linux/" if arch == "aarch64" else ""
    for path in [
        "lib/gcc/" + triple + "/" + _GCC["version"] + "/" + filename
        for filename in ["crtbegin.o", "crtend.o", "libgcc.a", "libgcc_eh.a", "include", "include-fixed"]
    ] + [
        cxx_prefix + "include/c++/" + _GCC["version"],
        cxx_prefix + "lib64/libstdc++.a",
        cxx_prefix + "lib64/libstdc++.so",
    ]:
        if not ctx.path(path).exists:
            fail("GCC archive is missing compiler-owned runtime input " + path)
    cxx_include = cxx_prefix + "include/c++/" + _GCC["version"]
    gcc_lib = "lib/gcc/" + triple + "/" + _GCC["version"]
    ctx.file("BUILD.bazel", """
load("@rules_cc//cc:cc_library.bzl", "cc_library")
load("@rules_cc//cc/toolchains:cc_toolchain.bzl", "cc_toolchain")
load(%r, "gcc_linux_cc_toolchain_config")

package(default_visibility = ["//visibility:public"])

gcc_linux_cc_toolchain_config(
    name = "config",
    arch = %r,
    triple = %r,
    version = %r,
    sysroot = %r,
)

filegroup(
    name = "files",
    srcs = glob(["bin/**", "xbin/**", "lib/**", "lib64/**", "libexec/**", "include/**", %r]) + [%r],
)

cc_library(
    name = "libstdcxx",
    srcs = [%r],
    hdrs = glob([%r]),
    includes = %r,
    linkstatic = True,
)

filegroup(
    name = "libgcc",
    srcs = %r,
)

cc_toolchain(
    name = "cc_toolchain",
    all_files = ":files",
    ar_files = ":files",
    as_files = ":files",
    compiler_files = ":files",
    dwp_files = ":files",
    linker_files = ":files",
    objcopy_files = ":files",
    strip_files = ":files",
    supports_param_files = True,
    toolchain_config = ":config",
)

exports_files(glob(["xbin/*"]))
""" % (
        str(ctx.attr._config),
        arch,
        triple,
        _GCC["version"],
        str(ctx.attr.sysroot),
        triple + "/**",
        str(ctx.attr.sysroot),
        cxx_prefix + "lib64/libstdc++.a",
        cxx_include + "/**",
        [cxx_include, cxx_include + "/" + triple, cxx_include + "/backward"],
        [gcc_lib + "/libgcc.a", gcc_lib + "/libgcc_eh.a"],
    ))

_gcc_repository = repository_rule(
    implementation = _gcc_repository_impl,
    attrs = {
        "arch": attr.string(mandatory = True, values = ["x86_64", "aarch64"]),
        "sysroot": attr.label(mandatory = True),
        "_config": attr.label(default = Label("//toolchains/gcc:toolchain.bzl")),
    },
)

def _gcc_extension_impl(ctx):
    for mod in ctx.modules:
        for tag in mod.tags.toolchain:
            _gcc_repository(
                name = tag.name,
                arch = tag.arch,
                sysroot = tag.sysroot,
            )
    return ctx.extension_metadata(reproducible = True)

gcc_extension = module_extension(
    implementation = _gcc_extension_impl,
    tag_classes = {
        "toolchain": tag_class(attrs = {
            "name": attr.string(mandatory = True),
            "arch": attr.string(mandatory = True, values = ["x86_64", "aarch64"]),
            "sysroot": attr.label(mandatory = True),
        }),
    },
)
