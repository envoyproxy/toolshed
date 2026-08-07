"""Protobuf toolchain helpers for consuming the registered prebuilt protoc.

The `@com_google_protobuf//bazel/private:proto_toolchain_type` target itself has
`visibility = ["//visibility:public"]`; what is private and must not be
imported directly are the helper .bzl files under `//bazel/private/`.

Usage in an aspect or rule:

    load("//bazel/toolchains:utils.bzl", "use_proto_toolchain", "get_proto_compiler")

    my_aspect = aspect(
        toolchains = use_proto_toolchain(),
        ...
    )

    def _impl(target, ctx):
        protoc = get_proto_compiler(ctx)          # FilesToRunProvider
        ctx.actions.run(executable = protoc, ...)

For genrule / $(location) consumers that need a runnable `$(location)`-able
protoc target, instantiate `proto_compiler_binary` in your BUILD file:

    load("//bazel/toolchains:utils.bzl", "proto_compiler_binary")

    proto_compiler_binary(name = "protoc", visibility = ["//visibility:public"])

Rules and aspects should use `use_proto_toolchain()` + `get_proto_compiler(ctx)`
directly rather than depending on a `proto_compiler_binary` target.
"""

# This is a plain string label.  It is resolved in the repo mapping of the
# consumer that uses the proto toolchain (e.g. envoy/envoy_api), where
# protobuf is already available via a bazel_dep or http_archive named
# com_google_protobuf.
PROTO_TOOLCHAIN_TYPE = "@com_google_protobuf//bazel/private:proto_toolchain_type"


def use_proto_toolchain(toolchain_type = PROTO_TOOLCHAIN_TYPE):
    """Returns the toolchains list to declare on an aspect or rule."""
    return [toolchain_type]


def get_proto_compiler(ctx, toolchain_type = PROTO_TOOLCHAIN_TYPE):
    """Returns the FilesToRunProvider for protoc from the registered proto toolchain."""
    toolchain = ctx.toolchains[toolchain_type]
    if not toolchain:
        fail("No proto toolchain registered for '%s'." % toolchain_type)
    return toolchain.proto.proto_compiler


def _proto_compiler_binary_impl(ctx):
    protoc = get_proto_compiler(ctx)  # FilesToRunProvider
    # Bazel requires executable rules to produce their own executable file;
    # create a symlink so the binary is "owned" by this rule while still
    # delegating to the toolchain-resolved protoc.
    exe = ctx.actions.declare_file(ctx.label.name)
    ctx.actions.symlink(output = exe, target_file = protoc.executable, is_executable = True)
    return [DefaultInfo(
        executable = exe,
        files = depset([exe]),
        runfiles = ctx.runfiles(files = [exe, protoc.executable]),
    )]


proto_compiler_binary = rule(
    implementation = _proto_compiler_binary_impl,
    executable = True,
    toolchains = use_proto_toolchain(),
    doc = "Exposes protoc from the registered proto toolchain as a runnable target " +
          "for genrule / $(location) consumers.",
)
