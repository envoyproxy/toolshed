"""Rule wrapping a `sq` executable as a toolshed OpenPGP signer.

The path of the `sq` executable is baked into the wrapper at analysis time so
that the signer does not need to resolve runfiles - signing actions run with
an empty environment.
"""

def _sq_signer_impl(ctx):
    sq_default = ctx.attr.sq[DefaultInfo]
    sq_files_to_run = sq_default.files_to_run
    sq_executable = sq_files_to_run.executable
    if not sq_executable:
        fail("`sq` (%s) does not provide an executable" % ctx.attr.sq.label)

    out = ctx.actions.declare_file("%s.sh" % ctx.label.name)
    ctx.actions.expand_template(
        template = ctx.file._template,
        output = out,
        substitutions = {"@SQ@": sq_executable.path},
        is_executable = True,
    )
    runfiles = ctx.runfiles(files = [sq_executable]).merge(sq_default.default_runfiles)
    return [DefaultInfo(
        executable = out,
        files = depset([out]),
        runfiles = runfiles,
    )]

sq_signer = rule(
    implementation = _sq_signer_impl,
    doc = "Wraps a `sq` executable as an implementation of the signer CLI contract.",
    attrs = {
        "sq": attr.label(
            doc = "The `sq` executable.",
            mandatory = True,
            executable = True,
            cfg = "exec",
        ),
        "_template": attr.label(
            default = "//pgp/private:signer.sh",
            allow_single_file = True,
        ),
    },
    executable = True,
)
