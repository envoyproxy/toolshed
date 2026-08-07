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

For genrule / $(location) consumers that need a runnable target, use
`proto_compiler_binary` instead of `use_proto_toolchain` + `get_proto_compiler`:

    load("//bazel/toolchains:utils.bzl", "proto_compiler_binary")

    proto_compiler_binary(name = "protoc", visibility = ["//visibility:public"])
"""

# This is a plain string label. It is resolved in the repo mapping of the
# consumer that uses the proto toolchain (e.g. envoy/envoy_api), where protobuf
# is already available. The toolshed bazel module must not add a protobuf
# bazel_dep for this.
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
    runfiles = ctx.runfiles()
    if protoc.default_runfiles:
        runfiles = runfiles.merge(protoc.default_runfiles)
    return [DefaultInfo(
        executable = protoc.executable,
        files = depset([protoc.executable]),
        runfiles = runfiles,
    )]


proto_compiler_binary = rule(
    implementation = _proto_compiler_binary_impl,
    executable = True,
    toolchains = use_proto_toolchain(),
    doc = "Exposes protoc from the registered proto toolchain as a runnable target " +
          "for genrule / $(location) consumers.",
)
