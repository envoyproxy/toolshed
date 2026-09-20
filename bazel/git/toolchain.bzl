"""Toolchain for hermetic git execution."""

GitInfo = provider(
    doc = "Information about a git implementation.",
    fields = {
        "git": "File: executable that behaves like `git` with no extra env required.",
        "runfiles": "runfiles needed by `git`.",
    },
)

def _merge_default_runfiles(ctx, runfiles, target):
    default = target[DefaultInfo]
    runfiles = runfiles.merge(ctx.runfiles(files = default.files.to_list()))
    if default.default_runfiles:
        # data_runfiles can pull in unrelated data closures from cc_binary-like targets.
        runfiles = runfiles.merge(default.default_runfiles)
    return runfiles

def _git_toolchain_impl(ctx):
    default = ctx.attr.git[DefaultInfo]
    executable = default.files_to_run.executable
    if not executable:
        fail("`git` (%s) does not provide an executable" % ctx.attr.git.label)

    runfiles = ctx.runfiles(files = [executable])
    runfiles = _merge_default_runfiles(ctx, runfiles, ctx.attr.git)
    for target in ctx.attr.data:
        runfiles = _merge_default_runfiles(ctx, runfiles, target)

    return [
        platform_common.ToolchainInfo(
            git = GitInfo(
                git = executable,
                runfiles = runfiles,
            ),
        ),
        platform_common.TemplateVariableInfo({"GIT": executable.path}),
    ]

git_toolchain = rule(
    implementation = _git_toolchain_impl,
    doc = "Declares a git implementation for `//git:toolchain_type`.",
    attrs = {
        "data": attr.label_list(
            cfg = "exec",
            default = [],
            doc = "Additional runtime files needed by `git`.",
        ),
        "git": attr.label(
            doc = "Executable implementing `git` with no extra environment required.",
            mandatory = True,
            executable = True,
            cfg = "exec",
        ),
    },
)
