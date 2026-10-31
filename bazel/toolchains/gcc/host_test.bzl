"""Unit tests for which toolchains `gcc_extension.host` swaps for the host GCC."""

load("@bazel_skylib//lib:unittest.bzl", "asserts", "unittest")
load(":host.bzl", "host_toolchain_names")

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
