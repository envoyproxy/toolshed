"""Test rule that exercises use_proto_toolchain() + get_proto_compiler() directly.

This simulates how a rule or aspect would consume the proto toolchain helpers,
independent of the proto_compiler_binary convenience target.
"""

load("//toolchains:utils.bzl", "get_proto_compiler", "use_proto_toolchain")

def _proto_compiler_version_impl(ctx):
    out = ctx.actions.declare_file(ctx.label.name + "_version.txt")
    protoc = get_proto_compiler(ctx)  # FilesToRunProvider
    ctx.actions.run_shell(
        outputs = [out],
        tools = [protoc],
        command = '"{bin}" --version > "{out}"'.format(
            bin = protoc.executable.path,
            out = out.path,
        ),
        mnemonic = "ProtocVersion",
        progress_message = "Running protoc --version",
    )
    return [DefaultInfo(files = depset([out]))]

proto_compiler_version = rule(
    implementation = _proto_compiler_version_impl,
    toolchains = use_proto_toolchain(),
    attrs = {},
    doc = "Runs protoc --version and captures the output to a file.",
)
