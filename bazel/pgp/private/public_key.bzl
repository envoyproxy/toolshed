"""Validation rule for committed OpenPGP public keys."""

def _pgp_public_key_impl(ctx):
    src = ctx.file.src
    out = ctx.actions.declare_file(src.basename)
    ctx.actions.run(
        executable = ctx.executable._validator,
        inputs = [src],
        outputs = [out],
        arguments = [src.path, out.path],
        tools = [ctx.executable._validator],
        mnemonic = "OpenPGPPublicKey",
        progress_message = "Validating OpenPGP public key %s" % src.short_path,
    )
    return [DefaultInfo(files = depset([out]))]

pgp_public_key = rule(
    implementation = _pgp_public_key_impl,
    doc = "Validate and re-emit an ASCII-armored OpenPGP public key.",
    attrs = {
        "src": attr.label(
            doc = "ASCII-armored public key file.",
            mandatory = True,
            allow_single_file = True,
        ),
        "_validator": attr.label(
            default = "//pgp/private:public_key_validator",
            executable = True,
            cfg = "exec",
        ),
    },
)
