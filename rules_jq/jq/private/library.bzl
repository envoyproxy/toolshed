"""Stage jq modules with stable import paths."""

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
    root = ctx.label.name + ".modules"

    # An empty marker file names each import root: as an ordinary file it resolves through
    # runfiles in both symlink-tree and manifest layouts, unlike a tree artifact.
    marker = ctx.actions.declare_file(root + "/.jq_root")
    ctx.actions.write(marker, "")
    imports = {}
    staged = [marker]
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
        output = ctx.actions.declare_file(root + "/" + path)
        ctx.actions.symlink(output = output, target_file = src)
        staged.append(output)
    runfiles = ctx.runfiles(files = staged)
    for dep in ctx.attr.deps:
        runfiles = runfiles.merge(dep[DefaultInfo].default_runfiles)
    return [
        DefaultInfo(files = depset(staged), runfiles = runfiles),
        JqInfo(
            transitive_srcs = depset(ctx.files.srcs, transitive = [dep[JqInfo].transitive_srcs for dep in ctx.attr.deps]),
            roots = depset([marker], transitive = [dep[JqInfo].roots for dep in ctx.attr.deps], order = "preorder"),
        ),
    ]

jq_library = rule(
    implementation = _jq_library_impl,
    doc = "Stage .jq and .json modules; direct roots precede dependency roots on collisions.",
    attrs = {
        "srcs": attr.label_list(allow_files = [".jq", ".json"]),
        "deps": attr.label_list(providers = [JqInfo]),
        "strip_import_prefix": attr.string(doc = "Package-relative prefix, or repository-relative if starting with '/'. For sources from an external repository, '../<repo>/' is stripped first, so a '/'-prefixed value is relative to that repository's root, not the main repository."),
        "import_prefix": attr.string(doc = "Prefix prepended to each stripped import path."),
    },
)
