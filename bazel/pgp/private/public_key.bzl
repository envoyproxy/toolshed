"""Validation rule for committed OpenPGP public keys."""

def _pgp_public_key_impl(ctx):
    src = ctx.file.src
    out = ctx.actions.declare_file(src.basename)
    ctx.actions.run_shell(
        inputs = [src],
        outputs = [out],
        arguments = [src.path, out.path],
        command = """\
set -eu
src="$1"
out="$2"

if ! grep -Fq -- '-----BEGIN PGP PUBLIC KEY BLOCK-----' "$src" \
    || ! grep -Fq -- '-----END PGP PUBLIC KEY BLOCK-----' "$src"; then
    echo "refusing non-public OpenPGP key: missing public key block" >&2
    exit 1
fi
if grep -Fq -- 'PRIVATE KEY' "$src"; then
    echo "refusing OpenPGP key containing PRIVATE KEY material" >&2
    exit 1
fi
if [[ "$(grep -Fc -- '-----BEGIN PGP' "$src")" -ne 1 ]]; then
    echo "refusing OpenPGP key containing multiple PGP blocks" >&2
    exit 1
fi
cp "$src" "$out"
""",
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
    },
)
