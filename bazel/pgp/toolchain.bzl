"""Toolchain for hermetic OpenPGP signing.

The toolchain provides an executable implementing the signer CLI contract
documented in `//pgp:README.md`:

```
signer --mode {detached|cleartext|inline} \\
       --key <encrypted-secret-key-file> \\
       --passphrase-file <abs-path> \\
       --require-encrypted-key \\
       --out <output-file> \\
       [--armor] \\
       <input>...
```

Any implementation of that contract can be dropped in without changing the
rules - the default implementation wraps Sequoia PGP's `sq`.
"""

PgpSignerInfo = provider(
    doc = "Information about an OpenPGP signer implementation.",
    fields = {
        "runfiles": "runfiles required by the signer executable.",
        "signer": "File: executable implementing the signer CLI contract.",
    },
)

def _pgp_toolchain_impl(ctx):
    default = ctx.attr.signer[DefaultInfo]
    executable = default.files_to_run.executable
    if not executable:
        fail("`signer` (%s) does not provide an executable" % ctx.attr.signer.label)
    return [platform_common.ToolchainInfo(
        pgp_signer = PgpSignerInfo(
            signer = executable,
            runfiles = default.default_runfiles,
        ),
    )]

pgp_toolchain = rule(
    implementation = _pgp_toolchain_impl,
    doc = "Declares an OpenPGP signer implementation for `//pgp:toolchain_type`.",
    attrs = {
        "signer": attr.label(
            doc = "Executable implementing the signer CLI contract.",
            mandatory = True,
            executable = True,
            cfg = "exec",
        ),
    },
)
