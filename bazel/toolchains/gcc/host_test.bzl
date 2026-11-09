"""Unit tests for which toolchains `gcc_extension.host` swaps, and which hosts fall back."""

load("@bazel_skylib//lib:unittest.bzl", "asserts", "unittest")
load(":host.bzl", "banner_major", "fallback_cpu_constraint", "fallback_host_cpu", "gcc_tool_names", "host_toolchain_names")

def _module(is_root, *toolchains):
    return struct(
        is_root = is_root,
        tags = struct(toolchain = [struct(name = name, arch = arch) for name, arch in toolchains]),
    )

def _host(toolchains = []):
    return struct(toolchains = toolchains)

# The root declares a native and a cross toolchain; a dependency declares a native one that it
# uses only for its `:libstdcxx`.
_MODULES = [
    _module(True, ("root_x86_64", "x86_64"), ("root_aarch64", "aarch64")),
    _module(False, ("dep_x86_64", "x86_64")),
]

def _host_toolchain_names_test_impl(ctx):
    env = unittest.begin(ctx)

    # Without `host`, everything is hermetic.
    asserts.equals(env, [], host_toolchain_names(_MODULES, None, None))

    # By default only the root's native-arch toolchains: the dependency's `:libstdcxx` stays
    # hermetic, and so does the cross toolchain.
    asserts.equals(env, ["root_x86_64"], host_toolchain_names(_MODULES, _host(), "x86_64"))
    asserts.equals(env, ["root_aarch64"], host_toolchain_names(_MODULES, _host(), "aarch64"))

    # Named toolchains are replaced from any module, and only those.
    asserts.equals(
        env,
        ["dep_x86_64"],
        host_toolchain_names(_MODULES, _host(["dep_x86_64"]), "x86_64"),
    )
    asserts.equals(
        env,
        ["root_x86_64", "dep_x86_64"],
        host_toolchain_names(_MODULES, _host(["root_x86_64", "dep_x86_64"]), "x86_64"),
    )

    # A named toolchain for another arch is never replaced.
    asserts.equals(env, [], host_toolchain_names(_MODULES, _host(["root_aarch64"]), "x86_64"))

    # No root toolchains: the default replaces nothing.
    asserts.equals(env, [], host_toolchain_names(_MODULES[1:], _host(), "x86_64"))
    return unittest.end(env)

host_toolchain_names_test = unittest.make(_host_toolchain_names_test_impl)

def _os(name, arch):
    return struct(name = name, arch = arch)

def _fallback_host_test_impl(ctx):
    env = unittest.begin(ctx)

    # The hermetic archives run on x86_64 Linux, so there is no fallback there.
    asserts.equals(env, None, fallback_host_cpu(_os("linux", "amd64")))
    asserts.equals(env, None, fallback_host_cpu(_os("linux", "x86_64")))

    # Other supported Linux hosts fall back to their own GCC.
    asserts.equals(env, "aarch64", fallback_host_cpu(_os("linux", "aarch64")))
    asserts.equals(env, "aarch64", fallback_host_cpu(_os("Linux", "arm64")))

    # Unsupported and non-Linux hosts are left alone rather than failing.
    asserts.equals(env, None, fallback_host_cpu(_os("linux", "s390x")))
    asserts.equals(env, None, fallback_host_cpu(_os("mac os x", "aarch64")))

    # The fallback toolchain is registered for the host's CPU, or for no platform at all.
    asserts.equals(env, "@platforms//cpu:aarch64", fallback_cpu_constraint("aarch64"))
    asserts.equals(env, "@platforms//:incompatible", fallback_cpu_constraint(None))
    return unittest.end(env)

fallback_host_test = unittest.make(_fallback_host_test_impl)

def _host_tools_test_impl(ctx):
    env = unittest.begin(ctx)

    # The plain name is tried first, then the names that mixed-release installations use.
    asserts.equals(
        env,
        ["gcov", "gcov-14", "aarch64-linux-gnu-gcov", "aarch64-linux-gnu-gcov-14"],
        gcc_tool_names("gcov", "aarch64-linux-gnu", "14"),
    )

    # A plain `gcov` from another release is told apart by its banner.
    asserts.equals(env, "14", banner_major("gcov (Debian 14.2.0-19) 14.2.0\nCopyright (C) 2024"))
    asserts.equals(env, "12", banner_major("gcov (Debian 12.2.0-14) 12.2.0"))
    asserts.equals(env, "14", banner_major("gcov (GCC) 14.2.1 20240912 (Red Hat 14.2.1-3)"))
    asserts.equals(env, "13", banner_major("cpp 13.4.0"))
    asserts.equals(env, None, banner_major("not a version"))
    asserts.equals(env, None, banner_major(""))
    return unittest.end(env)

host_tools_test = unittest.make(_host_tools_test_impl)
