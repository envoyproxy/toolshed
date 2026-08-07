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
`current_protoc_toolchain` instead of `use_proto_toolchain` + `get_proto_compiler`:

    load("//bazel/toolchains:utils.bzl", "current_protoc_toolchain")

    current_protoc_toolchain(name = "protoc", visibility = ["//visibility:public"])
"""

# This label is resolved in the repo mapping of toolshed, which now has
# protobuf as a bazel_dep (repo_name = "com_google_protobuf").
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


def _current_protoc_toolchain_impl(ctx):
    protoc = get_proto_compiler(ctx)  # FilesToRunProvider
    runfiles = ctx.runfiles()
    if protoc.default_runfiles:
        runfiles = runfiles.merge(protoc.default_runfiles)
    return [DefaultInfo(
        executable = protoc.executable,
        files = depset([protoc.executable]),
        runfiles = runfiles,
    )]


current_protoc_toolchain = rule(
    implementation = _current_protoc_toolchain_impl,
    executable = True,
    toolchains = use_proto_toolchain(),
    doc = "Exposes protoc from the registered proto toolchain as a runnable target " +
          "for genrule / $(location) consumers.",
)
