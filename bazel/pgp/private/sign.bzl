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
- no ambient environment is inherited (`use_default_shell_env = False`); only
  an explicit, minimal `PATH` is set.
"""

load("@bazel_skylib//rules:common_settings.bzl", "BuildSettingInfo")

TOOLCHAIN_TYPE = "//pgp:toolchain_type"

MODES = [
    "cleartext",
    "detached",
    "inline",
]

# Hardcoded, not user-overridable: a signing action must never be shipped to,
# or cached in, anything other than the machine it runs on. The action stays
# sandboxed and local - `local` (no-sandbox) is deliberately not one of these.
EXECUTION_REQUIREMENTS = {
    "no-cache": "1",
    "no-remote": "1",
    "no-remote-cache": "1",
    "no-remote-cache-upload": "1",
    "no-remote-exec": "1",
}

# Minimal, explicit `PATH` for signing/checksums actions. `env = {}` alone
# only works because bash/glibc fall back to compiled-in default paths -
# setting `PATH` explicitly makes that dependency visible and pinned rather
# than implicit.
_ACTION_ENV = {"PATH": "/usr/bin:/bin"}

MNEMONIC = "OpenPGPSign"

_NO_PATH = """
No {what} path configured for {label}.

OpenPGP signing requires an absolute host path to the {what_desc}.
Pass the absolute path:

  bazel build {label} --@envoy_toolshed//pgp:{setting_flag}=/abs/path

The file is read by the signer at execution time. Bazel never reads it, and it
must not live under the Bazel output tree or any artifact upload path.
"""

_RELATIVE_PATH = """
{what_cap} path for {label} is not absolute: {path}

Bazel actions do not run in your working directory, so the {what} path must
be absolute.
"""

_PASSPHRASE_FRAGMENT = """
Passphrase path for {label} specifies a fragment: {path}

Specifying a sha256 fragment on passphrase_path is forbidden: a passphrase digest is an oracle for weak passphrases.
"""

_BAD_FRAGMENT = """
Invalid sha256 fragment for {label}: {frag}

Expected a fragment in the form #sha256=<64 lowercase hex characters>.
"""

def _host_path(ctx, setting, what):
    value = setting[BuildSettingInfo].value
    what_cap = "Key" if what == "key" else "Passphrase"
    what_desc = "passphrase-encrypted secret key" if what == "key" else "passphrase file"
    setting_flag = "key_path" if what == "key" else "passphrase_path"

    if not value:
        fail(_NO_PATH.format(
            what = what,
            what_desc = what_desc,
            setting_flag = setting_flag,
            label = ctx.label,
        ))

    parts = value.split("#")
    if len(parts) > 2:
        fail("Invalid {what} path for {label}: contains multiple '#' characters".format(
            what = what,
            label = ctx.label,
        ))

    path = parts[0]
    if not path.startswith("/"):
        fail(_RELATIVE_PATH.format(
            what = what,
            what_cap = what_cap,
            label = ctx.label,
            path = path,
        ))

    sha256 = None
    if len(parts) == 2:
        frag = parts[1]
        if what == "passphrase":
            fail(_PASSPHRASE_FRAGMENT.format(label = ctx.label, path = value))

        if not frag.startswith("sha256=") or len(frag) != 71:
            fail(_BAD_FRAGMENT.format(label = ctx.label, frag = frag))

        digest = frag[7:]
        for c in digest.elems():
            if c not in "0123456789abcdef":
                fail(_BAD_FRAGMENT.format(label = ctx.label, frag = frag))
        sha256 = digest

    return struct(path = path, sha256 = sha256)

def _sign(ctx, mode, src, out, armor):
    key_info = _host_path(ctx, ctx.attr._key_path, "key")
    passphrase_info = _host_path(ctx, ctx.attr._passphrase_path, "passphrase")
    signer = ctx.toolchains[TOOLCHAIN_TYPE].pgp_signer
    args = ctx.actions.args()
    args.add("--mode", mode)
    args.add("--key", key_info.path)
    if key_info.sha256:
        args.add("--key-sha256", key_info.sha256)

    # Only the *path* is passed - never the passphrase itself, so it cannot
    # show up in `ps`, `--subcommands` or an execution log.
    args.add("--passphrase-file", passphrase_info.path)
    args.add("--require-encrypted-key")
    args.add("--out", out)
    if armor:
        args.add("--armor")
    args.add(src)
    ctx.actions.run(
        executable = signer.signer,
        arguments = [args],
        inputs = [src],
        outputs = [out],
        tools = depset([signer.signer], transitive = [signer.runfiles.files]),
        mnemonic = MNEMONIC,
        progress_message = "Signing %s" % out.short_path,
        execution_requirements = EXECUTION_REQUIREMENTS,
        use_default_shell_env = False,
        env = _ACTION_ENV,
    )

def _pgp_sign_impl(ctx):
    out = ctx.outputs.out
    _sign(
        ctx,
        mode = ctx.attr.mode,
        src = ctx.file.src,
        out = out,
        armor = ctx.attr.armor,
    )
    return [DefaultInfo(files = depset([out]))]

pgp_sign = rule(
    implementation = _pgp_sign_impl,
    doc = """Sign `src` with key specified via `--@envoy_toolshed//pgp:key_path`.

The key must be a passphrase-encrypted OpenPGP secret key host path. The
passphrase host path is provided via `--@envoy_toolshed//pgp:passphrase_path`.
""",
    attrs = {
        "armor": attr.bool(
            doc = "Emit ASCII armored output.",
            default = True,
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
        "src": attr.label(
            doc = "The single file to sign.",
            mandatory = True,
            allow_single_file = True,
        ),
        "_key_path": attr.label(
            default = "//pgp:key_path",
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
        env = _ACTION_ENV,
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
