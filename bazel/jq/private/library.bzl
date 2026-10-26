"""Stage jq modules with stable import paths."""

load("@bazel_skylib//lib:shell.bzl", "shell")
load(":providers.bzl", "JqInfo")

def _check_prefix(value, name):
    if value and any([part in ["", ".", ".."] for part in value.split("/")]):
        fail("%s must be a normalized path without '.' or '..': %r" % (name, value))

def _jq_library_impl(ctx):
    strip = ctx.attr.strip_import_prefix
    absolute = strip.startswith("/")
    strip = strip.removeprefix("/")
    _check_prefix(strip, "strip_import_prefix")
    _check_prefix(ctx.attr.import_prefix, "import_prefix")
    root = ctx.actions.declare_directory(ctx.label.name + ".modules")
    imports = {}
    commands = [
        "set -eu",
        "mkdir -p " + shell.quote(root.path),
        "touch " + shell.quote(root.path + "/.jq_root"),
    ]
    package_prefix = ctx.label.package + "/" if ctx.label.package else ""
    for src in ctx.files.srcs:
        if src.extension not in ["jq", "json"]:
            fail("jq_library sources must be .jq or .json files: %s" % src.path)
        path = src.short_path
        if path.startswith("../"):
            path = path.split("/", 2)[2]
        if not absolute:
            if not path.startswith(package_prefix):
                fail("source %s is outside package %s" % (src.short_path, ctx.label.package))
            path = path[len(package_prefix):]
        if strip:
            if not path.startswith(strip + "/"):
                fail("source %s is not beneath strip_import_prefix %r" % (src.short_path, ctx.attr.strip_import_prefix))
            path = path[len(strip) + 1:]
        if ctx.attr.import_prefix:
            path = ctx.attr.import_prefix + "/" + path
        if path.split("/")[0] == ".jq_root":
            fail("jq_library import path uses reserved marker name '.jq_root': %s" % path)
        if path in imports:
            fail("jq_library import-path collision at %r: %s and %s" % (path, imports[path].path, src.path))
        imports[path] = src
        destination = root.path + "/" + path

        # Copy rather than symlink so trees remain self-contained under remote execution.
        commands.extend([
            "mkdir -p " + shell.quote(destination.rsplit("/", 1)[0]),
            "cp -- %s %s" % (shell.quote(src.path), shell.quote(destination)),
        ])
    ctx.actions.run_shell(
        inputs = ctx.files.srcs,
        outputs = [root],
        command = "\n".join(commands),
        mnemonic = "JqStageModules",
    )
    return [
        DefaultInfo(files = depset([root])),
        JqInfo(
            transitive_srcs = depset(ctx.files.srcs, transitive = [dep[JqInfo].transitive_srcs for dep in ctx.attr.deps]),
            roots = depset([root], transitive = [dep[JqInfo].roots for dep in ctx.attr.deps], order = "preorder"),
        ),
    ]

jq_library = rule(
    implementation = _jq_library_impl,
    doc = "Stage .jq and .json modules; direct roots precede dependency roots on collisions.",
    attrs = {
        "srcs": attr.label_list(allow_files = [".jq", ".json"]),
        "deps": attr.label_list(providers = [JqInfo]),
        "strip_import_prefix": attr.string(doc = "Package-relative prefix, or workspace-relative if starting with '/'."),
        "import_prefix": attr.string(doc = "Prefix prepended to each stripped import path."),
    },
)
