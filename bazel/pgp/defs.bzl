"""Hermetic, secret-safe OpenPGP signing rules.

See `//pgp:README.md` for the security model.

Usage:

```starlark
load("@envoy_toolshed//pgp:defs.bzl", "pgp_sign_detached")

pgp_sign_detached(
    name = "sign_tarball",
    src = ":tarball",
)
```

```console
$ bazel build //:sign_tarball \\
      --@envoy_toolshed//pgp:key_path=/abs/path/to/key.asc \\
      --@envoy_toolshed//pgp:passphrase_path=/abs/path/to/passphrase
```
"""

load("//pgp/private:sign.bzl", _pgp_checksums = "pgp_checksums", _pgp_sign = "pgp_sign")
load("//pgp/private:sq.bzl", _sq_signer = "sq_signer")
load("//pgp:toolchain.bzl", _PgpSignerInfo = "PgpSignerInfo", _pgp_toolchain = "pgp_toolchain")

PgpSignerInfo = _PgpSignerInfo
pgp_sign = _pgp_sign
pgp_checksums = _pgp_checksums
pgp_toolchain = _pgp_toolchain
sq_signer = _sq_signer

def pgp_sign_detached(name, src, out = None, armor = True, **kwargs):
    """Create a detached signature for `src`.

    Args:
        name: Name of the target.
        src: File to sign.
        out: Output file, defaults to `<src>.asc`.
        armor: Emit ASCII armored output.
        **kwargs: Additional arguments to the underlying rule.
    """
    pgp_sign(
        name = name,
        src = src,
        mode = "detached",
        armor = armor,
        out = out or "%s.asc" % _basename(src),
        **kwargs
    )

def pgp_sign_cleartext(name, src, out = None, **kwargs):
    """Create a cleartext signed version of `src`.

    This is what `debsign` does to `.changes`/`.dsc` files, and what an apt
    `InRelease` file is.

    Args:
        name: Name of the target.
        src: File to sign.
        out: Output file, defaults to `<src>.asc`.
        **kwargs: Additional arguments to the underlying rule.
    """
    pgp_sign(
        name = name,
        src = src,
        mode = "cleartext",
        out = out or "%s.asc" % _basename(src),
        **kwargs
    )

def pgp_sign_checksums(
        name,
        srcs,
        algorithm = "sha256",
        out = None,
        checksums_out = None,
        **kwargs):
    """Generate a checksums file for `srcs` and cleartext sign it.

    Checksum generation is a separate, cacheable action - only the signing
    step handles secrets.

    Args:
        name: Name of the target.
        srcs: Files to checksum.
        algorithm: Checksum algorithm (`sha256` or `sha512`).
        out: Output file, defaults to `checksums.txt.asc`.
        checksums_out: Unsigned checksums file, defaults to `checksums.txt`.
        **kwargs: Additional arguments to the underlying signing rule.
    """
    checksums_out = checksums_out or "%s.checksums.txt" % name
    pgp_checksums(
        name = "%s_checksums" % name,
        srcs = srcs,
        algorithm = algorithm,
        out = checksums_out,
        tags = kwargs.get("tags"),
        visibility = kwargs.get("visibility"),
    )
    pgp_sign(
        name = name,
        src = "%s_checksums" % name,
        mode = "cleartext",
        out = out or "%s.asc" % checksums_out,
        **kwargs
    )

# TODO(pgp): this only clearsigns `changes` itself. Real `debsign` also signs
# the `.dsc`/`.buildinfo` files referenced by a `.changes` file and rewrites
# their sizes/hashes in the `Files:`/`Checksums-*` sections of the `.changes`
# before clearsigning it. Neither of those happen here - do not use this to
# produce a `.changes` file that itself references unsigned `.dsc`/
# `.buildinfo` files that need re-signing.
def pgp_sign_changes_file(name, changes, out = None, **kwargs):
    """Cleartext sign a single Debian `.changes` (or `.dsc`) file.

    This clearsigns `changes` itself - see the TODO above for what real
    `debsign` additionally does that this does not. The signed file replaces
    the original, so the output keeps the original basename (in a directory
    named after the target).

    Args:
        name: Name of the target.
        changes: The `.changes`/`.dsc` file to clearsign.
        out: Output file, defaults to `<name>/<basename of changes>`.
        **kwargs: Additional arguments to the underlying rule.
    """
    pgp_sign(
        name = name,
        src = changes,
        mode = "cleartext",
        out = out or "%s/%s" % (name, _basename(changes)),
        **kwargs
    )

def _basename(label):
    return str(label).split(":")[-1].split("/")[-1]
