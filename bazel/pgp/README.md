# OpenPGP signing (`//pgp`)

Hermetic, secret-safe OpenPGP signing rules.

Bazel has no notion of a secret: anything that is an action input is just
bytes that Bazel may hash, cache, upload to a CAS, or record in a build event
stream. These rules therefore make the safe configuration the *only*
configuration - the signing key must be passphrase-encrypted, the passphrase
is deliberately kept out of the build graph, and every signing action is
pinned to the local machine.

## Security model

### What these rules guarantee

| Guarantee | How |
| --- | --- |
| Only ciphertext key material ever enters the build graph | The signer is always invoked with `--require-encrypted-key` and fails hard if *any* secret key packet in the key file is unprotected |
| The passphrase is never an action input, and is never hashed, cached or uploaded by Bazel | It is provided as an absolute host path via `--@envoy_toolshed//pgp:passphrase_path`; Bazel only ever sees the path |
| The passphrase never appears on a command line (`ps`, `--subcommands`, execution log) | Only `--passphrase-file <path>` is passed |
| Signing actions never leave the machine | `no-remote`, `no-remote-exec`, `no-remote-cache`, `no-remote-cache-upload`, `no-cache` and `local` are hardcoded in the rule and are not user-overridable |
| Signing actions are greppable in `aquery` | `mnemonic = "OpenPGPSign"` |
| No ambient environment reaches the signer | `use_default_shell_env = False` and `env = {}`; the signer never consults `HOME`, `GNUPGHOME`, `SSH_AUTH_SOCK`, a gpg-agent socket, or any keyring/cert store on disk (`sq` is invoked with `--home none --cert-store none --key-store none --batch`) |
| The key is never copied into an output | The action writes only its declared output |
| A build without a configured passphrase fails loudly | The rule `fail()`s at analysis time |

### What you still own

| Concern | Why it is yours |
| --- | --- |
| The plaintext passphrase file on the host | It must exist in plaintext during the build. Put it somewhere dedicated - eg `${runner.temp}/gpg/passphrase`, `chmod 600`, deleted when the job ends - and **never** under the Bazel output tree, `--disk_cache`, or any artifact upload path |
| `--sandbox_debug` | It leaves sandbox directories (including the action's inputs) on disk |
| Visibility of the key target | Put the encrypted key behind a `package_group` so unrelated packages cannot depend on it |
| Where the encrypted key comes from | The rules verify it is encrypted, not that it is *your* key |
| `local` execution | The required `local` tag runs the action outside the sandbox. Isolation of the action is therefore provided by the empty environment and by the signer itself, not by the sandbox |

## Usage

```starlark
load("@envoy_toolshed//pgp:defs.bzl", "pgp_sign_checksums", "pgp_sign_detached")

pgp_sign_detached(
    name = "signed_tarball",
    src = ":tarball",
    key = ":signing-key.asc",
)

pgp_sign_checksums(
    name = "signed_checksums",
    srcs = [":tarball", ":package"],
    key = ":signing-key.asc",
)
```

```console
$ bazel build //:signed_tarball \
      --@envoy_toolshed//pgp:passphrase_path=/run/user/1000/gpg/passphrase
```

Without the flag the build fails at analysis time:

```
No passphrase path configured for //:signed_tarball.
```

### Rules

| Rule | Purpose |
| --- | --- |
| `pgp_sign(name, srcs, key, mode, out, armor)` | Core rule. `mode` is one of `detached`, `cleartext`, `inline` |
| `pgp_sign_detached(name, src, key, out)` | Detached, armored signature (`<src>.asc`) |
| `pgp_sign_cleartext(name, src, key, out)` | Cleartext signature - what `debsign` produces for `.changes`/`.dsc`, and what an apt `InRelease` is |
| `pgp_sign_checksums(name, srcs, key, algorithm, out)` | `shasum`-format checksums file for `srcs`, cleartext signed. Checksum generation is a separate, cacheable action - only signing handles secrets |
| `deb_sign_changes(name, changes, key, out)` | Cleartext sign a Debian `.changes`/`.dsc` file the way `debsign` would |
| `pgp_toolchain(name, signer)` | Register a signer implementation for `//pgp:toolchain_type` |

RPM header signing is **not** implemented here.

> TODO(pgp): RPM header signing needs an OpenPGP implementation that can
> insert a signature into the RPM header rather than produce a standalone
> signature. It is intended to arrive via the toolchain swap path below (a
> purpose-built `sequoia-openpgp` + `rpm-rs` signer in `rust/`), without any
> change to these rules.

## Toolchain

`//pgp:toolchain_type` is implemented by any executable satisfying the signer
CLI contract:

```
signer --mode {detached|cleartext|inline} \
       --key <encrypted-secret-key-file> \
       --passphrase-file <abs-path> \
       --require-encrypted-key \
       --out <output-file> \
       [--armor] \
       <input>
```

The default implementation is a thin wrapper around Sequoia PGP's
[`sq`](https://sequoia-pgp.org) - a Rust OpenPGP implementation with no agent,
home directory or keyring state, used as the OpenPGP backend for `rpm` on
Fedora/RHEL and as `sqv` in apt >= 3.0.

Upstream does not publish sha256-verifiable release binaries that could be
pinned here, so **no `sq` platform is fetched by default**. Enable the
platform(s) you need by supplying sha256s you have verified yourself:

```starlark
pgp_ext = use_extension("@envoy_toolshed//pgp:extensions.bzl", "pgp_extension")
pgp_ext.setup(
    sha256s = {
        "linux_x86_64": "<verified sha256 of the sq binary>",
    },
)
use_repo(pgp_ext, "sq_linux_x86_64")

register_toolchains("@sq_linux_x86_64//:toolchain")
```

`urls` can be used to point at your own audited mirror of the binary.

Swapping in a different signer (for example a purpose-built Rust signer) is a
matter of registering another toolchain - the rules do not change:

```starlark
pgp_toolchain(
    name = "my_signer_toolchain",
    signer = "//my/signer",
)

toolchain(
    name = "my_toolchain",
    toolchain = ":my_signer_toolchain",
    toolchain_type = "@envoy_toolshed//pgp:toolchain_type",
)
```

## Auditing your own targets

`//pgp/test:audit` runs `bazel aquery` over target patterns you give it and
asserts that:

1. every `OpenPGPSign` action carries all of the required execution
   requirements,
2. no action in the queried universe has an input matching
   `(^|/)\.gnupg(/|$)|private-keys-v1\.d|passphrase`,
3. no `OpenPGPSign` action has `HOME`, `GNUPGHOME` or `SSH_AUTH_SOCK` in its
   environment,
4. no `OpenPGPSign` action passes a forbidden string (eg your passphrase) on
   the command line.

```console
$ bazel run @envoy_toolshed//pgp/test:audit -- \
      --forbid "$(cat /run/user/1000/gpg/passphrase)" \
      "deps(//distribution:signed)"
```

Use `deps(...)` to audit the whole universe reachable from a target rather
than only the actions the target itself owns.

The script also accepts previously captured output:

```console
$ bazel aquery --output=jsonproto "deps(//distribution:signed)" > aquery.json
$ .../audit_test.sh --aquery-json aquery.json
```

`//pgp/test:audit_test` runs the audit against captured `aquery` output for
the example targets in `//pgp/test`, together with deliberately broken
fixtures (a removed execution requirement, a leaked environment variable, key
material as an action input, a passphrase on the command line), each of which
the audit must reject.

## Alternative: signing after the build

The most conservative option remains signing *outside* the build graph:
`bazel build` produces the unsigned artifacts and a separate `bazel run`
target signs them on the host. Nothing that happens in `bazel run` is an
action, so nothing is hashed, cached or uploaded.

The toolchain here is deliberately reusable for that: the same signer binary
can be driven from a `bazel run` wrapper via the CLI contract above.
