"""Runfiles-aware jq executables."""

load("@bazel_skylib//lib:shell.bzl", "shell")
load(":providers.bzl", "JQ_TOOLCHAIN_TYPE", "JqInfo")

# Forward the launcher's positional arguments. `"$@"` alone is an unbound
# variable under `set -u` in bash < 4.4 (macOS ships 3.2) when argv is empty;
# `${1+"$@"}` expands to nothing in that case and to `"$@"` otherwise.
ARGV = '${1+"$@"}'

def runfile_path(ctx, file):
    """Return a canonical runfiles key, also for external repositories."""
    if file.short_path.startswith("../"):
        return file.short_path[3:]
    return "%s/%s" % (ctx.workspace_name, file.short_path)

def location(ctx, file):
    """Return a shell expression resolving a File through runfiles."""
    return '"$(rlocation %s)"' % shell.quote(runfile_path(ctx, file))

def launcher(ctx, command, files, dependencies = [], roots = []):
    """Expand the common launcher and collect its complete runfiles.

    Args:
        ctx: Rule context with _launcher and _runfiles attributes.
        command: Shell command to append after runfiles initialization.
        files: Runtime Files, including staged module trees.
        dependencies: Targets whose default runfiles should be merged.
        roots: Staged `.jq_root` markers whose directories to resolve before running command.

    Returns:
        DefaultInfo with the executable launcher and runtime closure.
    """
    output = ctx.actions.declare_file(ctx.label.name + ".sh")

    # Resolve each root into a JQ_ROOT_<n> variable ahead of the command: a
    # plain assignment aborts under `set -e` when jq_root fails, whereas a
    # `$(...)` in argument position would not. Prepending while iterating
    # forward leaves the assignments in ascending order in the script. The
    # launcher's jq_root receives each root's `.jq_root` marker key.
    for i, root in enumerate(roots):
        command = 'JQ_ROOT_%d="$(jq_root %s)"\n%s' % (i, shell.quote(runfile_path(ctx, root)), command)
    ctx.actions.expand_template(
        template = ctx.file._launcher,
        output = output,
        substitutions = {"@@COMMAND@@": command},
        is_executable = True,
    )
    runfiles = ctx.runfiles(files = files).merge(ctx.attr._runfiles[DefaultInfo].default_runfiles)
    for dep in dependencies:
        runfiles = runfiles.merge(dep[DefaultInfo].default_runfiles)
    return DefaultInfo(executable = output, runfiles = runfiles)

def jq_info(deps):
    """Combine dependency module closures without changing their order."""
    return JqInfo(
        transitive_srcs = depset(transitive = [dep[JqInfo].transitive_srcs for dep in deps]),
        roots = depset(transitive = [dep[JqInfo].roots for dep in deps], order = "preorder"),
    )

def jq_command(ctx, roots):
    """Resolve the jq toolchain and ordered module search flags.

    Args:
        ctx: Rule context resolving JQ_TOOLCHAIN_TYPE.
        roots: Ordered staged `.jq_root` markers.

    Returns:
        The jq File and a shell expression invoking jq with -L flags.
    """
    jq = ctx.toolchains[JQ_TOOLCHAIN_TYPE].jqinfo.bin
    command = location(ctx, jq)
    for i in range(len(roots)):
        command += ' -L "$JQ_ROOT_%d"' % i
    return jq, command

def _jq_binary_impl(ctx):
    if bool(ctx.file.main) == bool(ctx.attr.filter):
        fail("jq_binary requires exactly one of main or filter")
    info = jq_info(ctx.attr.deps)
    roots = info.roots.to_list()
    jq, command = jq_command(ctx, roots)
    files = [jq] + roots
    command += " " + " ".join([shell.quote(arg) for arg in ctx.attr.jq_args])
    for target, names in ctx.attr.named_srcs.items():
        srcs = target[DefaultInfo].files.to_list()
        if len(srcs) != 1:
            fail("named_srcs target %s must provide exactly one file" % target.label)
        files.extend(srcs)
        for name in json.decode(names):
            command += " --slurpfile %s %s" % (shell.quote(name), location(ctx, srcs[0]))
    if ctx.file.main:
        files.append(ctx.file.main)
        command += " -f " + location(ctx, ctx.file.main)
    else:
        # A leading space keeps jq from reading a program such as `-length` as an option.
        command += " " + shell.quote(" " + ctx.attr.filter)
    return [
        launcher(ctx, "exec %s %s" % (command, ARGV), files + ctx.files.data, ctx.attr.data + ctx.attr.deps, roots),
        info,
    ]

_jq_binary = rule(
    implementation = _jq_binary_impl,
    executable = True,
    attrs = {
        "main": attr.label(allow_single_file = [".jq"]),
        "filter": attr.string(),
        "deps": attr.label_list(providers = [JqInfo]),
        "jq_args": attr.string_list(),
        "data": attr.label_list(allow_files = True),
        "named_srcs": attr.label_keyed_string_dict(allow_files = True),
        "_launcher": attr.label(default = Label("//jq/private:launcher.sh.tpl"), allow_single_file = True),
        "_runfiles": attr.label(default = Label("@bazel_tools//tools/bash/runfiles")),
    },
    toolchains = [JQ_TOOLCHAIN_TYPE],
)

def jq_binary(name, main = None, filter = "", deps = [], jq_args = [], named_srcs = {}, data = [], **kwargs):
    """Create an executable jq filter with staged modules and named slurpfiles.

    Args:
        name: Executable target name.
        main: Main .jq file, mutually exclusive with filter.
        filter: Inline jq program, mutually exclusive with main.
        deps: Targets providing JqInfo.
        jq_args: jq flags placed before the program.
        named_srcs: Mapping from variable names to single-file labels.
        data: Additional runtime files and targets.
        **kwargs: Common rule attributes.
    """
    # Group by resolved label, so equivalent spellings (`input.json`, `:input.json`) of one
    # source bind all their variables rather than becoming duplicate dict keys.
    bindings = {}
    for variable, source in named_srcs.items():
        bindings.setdefault(native.package_relative_label(source), []).append(variable)
    _jq_binary(
        name = name,
        main = main,
        filter = filter,
        deps = deps,
        jq_args = jq_args,
        data = data,
        named_srcs = {source: json.encode(names) for source, names in bindings.items()},
        **kwargs
    )
