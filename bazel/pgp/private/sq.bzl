"""Rule wrapping a `sq` binary as a toolshed OpenPGP signer.

The path of the `sq` binary is baked into the wrapper at analysis time so
that the signer does not need to resolve runfiles - signing actions run with
an empty environment.
"""

def _sq_signer_impl(ctx):
    out = ctx.actions.declare_file("%s.sh" % ctx.label.name)
    ctx.actions.expand_template(
        template = ctx.file._template,
        output = out,
        substitutions = {"@SQ@": ctx.file.sq.path},
        is_executable = True,
    )
    return [DefaultInfo(
        executable = out,
        files = depset([out]),
        runfiles = ctx.runfiles(files = [ctx.file.sq]),
    )]

sq_signer = rule(
    implementation = _sq_signer_impl,
    doc = "Wraps a `sq` binary as an implementation of the signer CLI contract.",
    attrs = {
        "sq": attr.label(
            doc = "The `sq` binary.",
            mandatory = True,
            allow_single_file = True,
        ),
        "_template": attr.label(
            default = "//pgp/private:signer.sh",
            allow_single_file = True,
        ),
    },
    executable = True,
)
