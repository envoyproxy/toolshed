"""Pinned x86_64-hosted GCC cross compilers using the shared base sysroot."""

load("//:versions.bzl", "VERSIONS")
load(":host.bzl", "gcc_host_repository", "host_cpu")

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

    # Give the multicall lld binary its GNU driver name. Bazel stages this
    # file symlink as an input, including in sandboxes, RBE and test runfiles.
    ctx.symlink(ctx.path(ctx.attr.lld), "bin/ld.lld")

    # These archives do not ship dwp; use the hermetic llvm-dwp, which packages
    # GCC's (DWARF 5) split debug info, never a host executable.
    ctx.symlink(ctx.path(ctx.attr.dwp), "bin/" + prefix + "dwp")
    for tool in ["ar", "as", "cpp", "gcc", "gcov", "ld", "nm", "objcopy", "objdump", "readelf", "strip"]:
        binary = "bin/" + prefix + tool
        if not ctx.path(binary).exists:
            fail("GCC archive is missing " + binary)

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
    prefix = %r,
    version = %r,
    sysroot = %r,
)

filegroup(
    name = "files",
    srcs = glob(["bin/**", "lib/**", "lib64/**", "libexec/**", "include/**", %r]) + [%r, %r, %r],
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

exports_files(glob(["bin/*"]))
""" % (
        str(ctx.attr._config),
        arch,
        triple,
        prefix,
        _GCC["version"],
        str(ctx.attr.sysroot),
        triple + "/**",
        str(ctx.attr.sysroot),
        str(ctx.attr.lld),
        str(ctx.attr.dwp),
        cxx_prefix + "lib64/libstdc++.a",
        cxx_include + "/**",
        [cxx_include, cxx_include + "/" + triple, cxx_include + "/backward"],
        [gcc_lib + "/libgcc.a", gcc_lib + "/libgcc_eh.a"],
    ))

_gcc_repository = repository_rule(
    implementation = _gcc_repository_impl,
    attrs = {
        "arch": attr.string(mandatory = True, values = ["x86_64", "aarch64"]),
        "dwp": attr.label(mandatory = True, allow_single_file = True),
        "lld": attr.label(mandatory = True, allow_single_file = True),
        "sysroot": attr.label(mandatory = True),
        "_config": attr.label(default = Label("//toolchains/gcc:toolchain.bzl")),
    },
)

def _gcc_extension_impl(ctx):
    host = None
    for mod in ctx.modules:
        for tag in mod.tags.host:
            if not mod.is_root:
                fail("gcc_extension.host may only be set by the root module")
            if host != None:
                fail("gcc_extension.host may only be set once")
            host = tag

    # Only an explicit `host` tag swaps native-arch toolchains for the host GCC
    # (all of them, or just those named in `host.toolchains`); every other
    # toolchain is the hermetic download.
    host_arch = host_cpu(ctx.os) if host else None
    names = [tag.name for mod in ctx.modules for tag in mod.tags.toolchain]
    for name in (host.toolchains if host else []):
        if name not in names:
            fail("gcc_extension.host(toolchains = ...) names unknown toolchain %r" % name)
    for mod in ctx.modules:
        for tag in mod.tags.toolchain:
            if host and tag.arch == host_arch and (not host.toolchains or tag.name in host.toolchains):
                gcc_host_repository(
                    name = tag.name,
                    arch = tag.arch,
                    gcc_version = host.gcc_version,
                    path = host.path,
                )
            else:
                _gcc_repository(
                    name = tag.name,
                    arch = tag.arch,
                    dwp = tag.dwp,
                    lld = tag.lld,
                    sysroot = tag.sysroot,
                )
    return ctx.extension_metadata(reproducible = not host)

gcc_extension = module_extension(
    implementation = _gcc_extension_impl,
    tag_classes = {
        "toolchain": tag_class(attrs = {
            "name": attr.string(mandatory = True),
            "arch": attr.string(mandatory = True, values = ["x86_64", "aarch64"]),
            "dwp": attr.label(mandatory = True, doc = "llvm-dwp executable, eg @llvm_minimal_linux_x64//:bin/llvm-dwp."),
            "lld": attr.label(mandatory = True),
            "sysroot": attr.label(mandatory = True),
        }),
        "host": tag_class(attrs = {
            "path": attr.string(mandatory = True, doc = "Absolute GCC installation prefix containing bin/gcc (e.g. /usr)."),
            "gcc_version": attr.string(doc = "Optional; if set, its major version must match the installed GCC."),
            "toolchains": attr.string_list(doc = "Optional; names of the native-arch toolchains to replace. Defaults to all of them."),
        }),
    },
)
