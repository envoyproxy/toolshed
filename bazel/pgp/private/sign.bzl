"""Implementation of the OpenPGP signing rules.

Security model (see `//pgp:README.md`):

- the secret key *must* be passphrase-encrypted, and the signer is always
  invoked with `--require-encrypted-key` so it fails hard on unprotected
  secret key packets. The only key material Bazel ever sees is ciphertext.
- the passphrase is deliberately not part of the build graph. It is provided
  as an absolute host path via `--@envoy_toolshed//pgp:passphrase_path`, so
  only the *path* is ever hashed, logged or cached.
- every signing action carries the full set of execution requirements below,
  hardcoded here rather than left to the caller.
- no environment is inherited (`use_default_shell_env = False`, `env = {}`).
"""

load("@bazel_skylib//rules:common_settings.bzl", "BuildSettingInfo")

TOOLCHAIN_TYPE = "//pgp:toolchain_type"

MODES = [
    "cleartext",
    "detached",
    "inline",
]

# Hardcoded, not user-overridable: a signing action must never be shipped to,
# or cached in, anything other than the machine it runs on.
EXECUTION_REQUIREMENTS = {
    "local": "1",
    "no-cache": "1",
    "no-remote": "1",
    "no-remote-cache": "1",
    "no-remote-cache-upload": "1",
    "no-remote-exec": "1",
}

MNEMONIC = "OpenPGPSign"

_NO_PASSPHRASE_PATH = """
No passphrase path configured for {label}.

OpenPGP signing requires a passphrase-encrypted secret key, and the passphrase
is deliberately not part of the build graph. Pass the absolute path of a file
containing the passphrase:

  bazel build {label} --@envoy_toolshed//pgp:passphrase_path=/abs/path/to/passphrase

The file is read by the signer at execution time. Bazel never reads it, and it
must not live under the Bazel output tree or any artifact upload path.
"""

_RELATIVE_PASSPHRASE_PATH = """
Passphrase path for {label} is not absolute: {path}

Bazel actions do not run in your working directory, so the passphrase path must
be absolute.
"""

def _passphrase_path(ctx):
    path = ctx.attr._passphrase_path[BuildSettingInfo].value
    if not path:
        fail(_NO_PASSPHRASE_PATH.format(label = ctx.label))
    if not path.startswith("/"):
        fail(_RELATIVE_PASSPHRASE_PATH.format(label = ctx.label, path = path))
    return path

def _sign(ctx, mode, srcs, key, out, armor):
    passphrase_path = _passphrase_path(ctx)
    signer = ctx.toolchains[TOOLCHAIN_TYPE].pgp_signer
    args = ctx.actions.args()
    args.add("--mode", mode)
    args.add("--key", key)

    # Only the *path* is passed - never the passphrase itself, so it cannot
    # show up in `ps`, `--subcommands` or an execution log.
    args.add("--passphrase-file", passphrase_path)
    args.add("--require-encrypted-key")
    args.add("--out", out)
    if armor:
        args.add("--armor")
    args.add_all(srcs)
    ctx.actions.run(
        executable = signer.signer,
        arguments = [args],
        inputs = srcs + [key],
        outputs = [out],
        tools = depset([signer.signer], transitive = [signer.runfiles.files]),
        mnemonic = MNEMONIC,
        progress_message = "Signing %s" % out.short_path,
        execution_requirements = EXECUTION_REQUIREMENTS,
        use_default_shell_env = False,
        env = {},
    )

def _pgp_sign_impl(ctx):
    out = ctx.outputs.out
    _sign(
        ctx,
        mode = ctx.attr.mode,
        srcs = ctx.files.srcs,
        key = ctx.file.key,
        out = out,
        armor = ctx.attr.armor,
    )
    return [DefaultInfo(files = depset([out]))]

pgp_sign = rule(
    implementation = _pgp_sign_impl,
    doc = """Sign `srcs` with `key`.

The key must be a passphrase-encrypted OpenPGP secret key. The passphrase is
provided out of band, see `--@envoy_toolshed//pgp:passphrase_path`.
""",
    attrs = {
        "armor": attr.bool(
            doc = "Emit ASCII armored output.",
            default = True,
        ),
        "key": attr.label(
            doc = "Passphrase-encrypted OpenPGP secret key.",
            mandatory = True,
            allow_single_file = True,
        ),
        "mode": attr.string(
            doc = "Signature mode.",
            default = "detached",
            values = MODES,
        ),
        "out": attr.output(
            doc = "Output file.",
            mandatory = True,
        ),
        "srcs": attr.label_list(
            doc = "Files to sign.",
            mandatory = True,
            allow_files = True,
        ),
        "_passphrase_path": attr.label(
            default = "//pgp:passphrase_path",
        ),
    },
    toolchains = [TOOLCHAIN_TYPE],
)

def _pgp_checksums_impl(ctx):
    out = ctx.outputs.out
    args = ctx.actions.args()
    args.add(ctx.attr.algorithm)
    args.add(out)
    args.add_all(ctx.files.srcs)
    ctx.actions.run(
        executable = ctx.executable._checksums,
        arguments = [args],
        inputs = ctx.files.srcs,
        outputs = [out],
        mnemonic = "OpenPGPChecksums",
        progress_message = "Generating checksums %s" % out.short_path,
        use_default_shell_env = False,
        env = {},
    )
    return [DefaultInfo(files = depset([out]))]

pgp_checksums = rule(
    implementation = _pgp_checksums_impl,
    doc = """Generate a `shasum`-format checksums file for `srcs`.

This action holds no secrets and is deliberately cacheable - only the
signing of the resulting file is a secret action.
""",
    attrs = {
        "algorithm": attr.string(
            doc = "Checksum algorithm.",
            default = "sha256",
            values = ["sha256", "sha512"],
        ),
        "out": attr.output(
            doc = "Output file.",
            mandatory = True,
        ),
        "srcs": attr.label_list(
            doc = "Files to checksum.",
            mandatory = True,
            allow_files = True,
        ),
        "_checksums": attr.label(
            default = "//pgp/private:checksums",
            executable = True,
            cfg = "exec",
        ),
    },
)
