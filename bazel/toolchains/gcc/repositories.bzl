"""Pinned x86_64-hosted hermetic GCC cross compilers, and the host GCC, for WORKSPACE."""

load("//:versions.bzl", "VERSIONS")
load(":host.bzl", "fallback_cpu_constraint", "fallback_host_cpu", "gcc_host_setup", "host_cpu")

_GCC = VERSIONS["gcc_toolchain"]

# The fallback host GCC toolchain, and the platform it is registered for.
_FALLBACK = "gcc_host"
_FALLBACK_PLATFORM = "gcc_host_platform"

def _gcc_hermetic_setup(ctx):
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
load(%r, "gcc_hermetic_cc_toolchain_config")

package(default_visibility = ["//visibility:public"])

gcc_hermetic_cc_toolchain_config(
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

_HERMETIC_ATTRS = {
    "arch": attr.string(mandatory = True, values = ["x86_64", "aarch64"]),
    "dwp": attr.label(mandatory = True, allow_single_file = True, doc = "llvm-dwp executable."),
    "lld": attr.label(mandatory = True, allow_single_file = True),
    "sysroot": attr.label(mandatory = True),
    "_config": attr.label(default = Label("//toolchains/gcc:hermetic.bzl")),
}

def _gcc_repository_impl(ctx):
    _gcc_hermetic_setup(ctx)

gcc_repository = repository_rule(
    implementation = _gcc_repository_impl,
    attrs = _HERMETIC_ATTRS,
    doc = """A hermetic GCC, as `@<name>//:cc_toolchain`, which runs on Linux x86_64.

It is not registered: wrap it in a `toolchain()` with the constraints or `target_settings` that
should select it.""",
)

def _gcc_host_override_repository_impl(ctx):
    # Only a native-arch toolchain is swapped for the host GCC: a cross toolchain, or one for
    # x86_64 remote workers from another host, stays hermetic.
    if ctx.os.name.lower().startswith("linux") and host_cpu(ctx.os) == ctx.attr.arch:
        gcc_host_setup(ctx, ctx.attr.arch, ctx.attr.host_path, ctx.attr.host_gcc_version)
    else:
        _gcc_hermetic_setup(ctx)

_gcc_host_override_repository = repository_rule(
    implementation = _gcc_host_override_repository_impl,
    environ = ["PATH"],
    local = True,
    attrs = dict(
        _HERMETIC_ATTRS,
        host_gcc_version = attr.string(default = ""),
        host_path = attr.string(mandatory = True),
    ),
    doc = "The host GCC at `host_path` where the toolchain is for the host's arch, else the hermetic GCC.",
)

def _gcc_fallback_repository_impl(ctx):
    arch = fallback_host_cpu(ctx.os)
    if arch:
        gcc_host_setup(ctx, arch, ctx.attr.path, ctx.attr.gcc_version)
        return

    # A registered toolchain names `:cc_toolchain` whether or not it can ever match, so keep
    # the label loadable (eg for `bazel query`) on hosts with no fallback.
    ctx.file("BUILD.bazel", """
# This host runs the hermetic GCC archives, or is not supported: there is no fallback.
filegroup(
    name = "cc_toolchain",
    visibility = ["//visibility:public"],
)
""")

_gcc_fallback_repository = repository_rule(
    implementation = _gcc_fallback_repository_impl,
    environ = ["PATH"],
    local = True,
    attrs = {
        "gcc_version": attr.string(default = ""),
        "path": attr.string(default = "", doc = "GCC installation prefix; empty uses the GCC that `gcc` on PATH runs."),
    },
    doc = "The host GCC on Linux hosts that no hermetic archive runs on (eg aarch64).",
)

def _gcc_host_platform_repository_impl(ctx):
    ctx.file("BUILD.bazel", """
package(default_visibility = ["//visibility:public"])

alias(
    name = "cpu",
    actual = %r,
)
""" % fallback_cpu_constraint(fallback_host_cpu(ctx.os)))

# The CPU constraint of the platform that the fallback toolchain both runs on and targets. It is
# a separate repository from the toolchain so that registering it does not probe for a host GCC
# during toolchain resolution.
_gcc_host_platform_repository = repository_rule(
    implementation = _gcc_host_platform_repository_impl,
)

def setup_gcc_toolchains(
        name = "gcc_linux_x86_64",
        arch = "x86_64",
        dwp = "@llvm_minimal_linux_x64//:bin/llvm-dwp",
        lld = "@llvm_minimal_linux_x64//:bin/lld",
        sysroot = "@sysroot_linux_amd64//:sysroot",
        host_path = None,
        host_gcc_version = ""):
    """Setup function for WORKSPACE to configure GCC.

    The toolchain is hermetic unless `host_path` is set. It needs `setup_llvm_minimal` and
    `setup_sysroots`, or equivalents, to be given.

    Also defines `@gcc_host`, the host's own GCC on Linux hosts that no hermetic archive runs
    on (eg aarch64), and `@gcc_host_platform`, for `//toolchains/gcc:linux_host_toolchain`.

    Args:
        name: Repository name.
        arch: Target CPU (`x86_64` or `aarch64`). The compiler runs on x86_64 either way.
        dwp: Label of an llvm-dwp executable.
        lld: Label of an lld executable.
        sysroot: Label exporting the glibc sysroot.
        host_path: Absolute GCC installation prefix containing bin/gcc (eg /usr). If set, and
            the toolchain is for the host's arch, it is the host GCC and not the hermetic one.
        host_gcc_version: Optional; if set, its major version must match the installed GCC.
    """
    if name in [_FALLBACK, _FALLBACK_PLATFORM]:
        fail("setup_gcc_toolchains(name = %r) is reserved for the host GCC fallback" % name)
    if host_path:
        _gcc_host_override_repository(
            name = name,
            arch = arch,
            dwp = dwp,
            lld = lld,
            sysroot = sysroot,
            host_gcc_version = host_gcc_version,
            host_path = host_path,
        )
    else:
        gcc_repository(
            name = name,
            arch = arch,
            dwp = dwp,
            lld = lld,
            sysroot = sysroot,
        )
    if not native.existing_rule(_FALLBACK):
        _gcc_fallback_repository(
            name = _FALLBACK,
            gcc_version = host_gcc_version,
            path = host_path or "",
        )
    if not native.existing_rule(_FALLBACK_PLATFORM):
        _gcc_host_platform_repository(name = _FALLBACK_PLATFORM)
