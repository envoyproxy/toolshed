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
| **No key material ever enters the build graph** | The key is a host path, not an artifact; the signer additionally refuses unencrypted keys (`--require-encrypted-key`) so even the host file is ciphertext |
| Key content is part of the action key | `key_path` accepts `#sha256=`; the digest is in the action key and verified by the signer before use |
| Passphrase changes always take effect | The passphrase is never hashed (a digest would be an offline oracle for weak passphrases); instead signing actions are `no-cache` and therefore always re-run |
| The passphrase is never an action input, and is never hashed, cached or uploaded by Bazel | It is provided as an absolute host path via `--@envoy_toolshed//pgp:passphrase_path`; Bazel only ever sees the path |
| The passphrase never appears on a command line (`ps`, `--subcommands`, execution log) | Only `--passphrase-file <path>` is passed |
| The passphrase is never written to disk a second time | The signer reads it via process substitution (`--password-file <(...)`) rather than copying it to a temporary file |
| Signing actions never leave the machine | `no-remote`, `no-remote-exec`, `no-remote-cache`, `no-remote-cache-upload` and `no-cache` are hardcoded in the rule and are not user-overridable |
| Signing actions stay sandboxed | Unlike a `local`-tagged action, sandboxing is never disabled, so the signer cannot see anything on disk it was not explicitly given as an input |
| Signing actions are greppable in `aquery` | `mnemonic = "OpenPGPSign"` |
| No ambient environment reaches the signer | `use_default_shell_env = False` and an explicit, minimal `env = {"PATH": "/usr/bin:/bin"}`; the signer never consults `HOME`, `GNUPGHOME`, `SSH_AUTH_SOCK`, a gpg-agent socket, or any keyring/cert store on disk (`sq` is invoked with `--home none --cert-store none --key-store none --batch`) |
| The key is never copied into an output | The action writes only its declared output |
| A build without a configured passphrase or key fails loudly | The rule `fail()`s at analysis time |

### What you still own

| Concern | Why it is yours |
| --- | --- |
| The encrypted key file on the host | Put it somewhere dedicated - eg `${runner.temp}/gpg/signing-key.asc`, `chmod 600`, deleted when the job ends - and **never** under the Bazel output tree, `--disk_cache`, or any artifact upload path |
| Computing key digest | Compute the `#sha256=` fragment yourself (eg `sha256sum`) — the rules cannot |
| The passphrase file contents | Trailing newlines are stripped (matching `gpg --passphrase-file`); everything else is used verbatim |
| The plaintext passphrase file on the host | It must exist in plaintext during the build. Put it somewhere dedicated - eg `${runner.temp}/gpg/passphrase`, `chmod 600`, deleted when the job ends - and **never** under the Bazel output tree, `--disk_cache`, or any artifact upload path |
| `--sandbox_debug` | It leaves sandbox directories (including the action's inputs) on disk |
| Where the encrypted key comes from | The rules verify it is encrypted, not that it is *your* key |

### Why not a label / why not `path_flag`

Hermeticity is about action inputs; the key and passphrase are deliberately host capabilities (like `SSH_AUTH_SOCK`), invisible to remote executors because `no-remote-exec` guarantees they never see the action; a label or path-flag would pull content into the graph, which is exactly what we are avoiding.

## Usage

```starlark
load("@envoy_toolshed//pgp:defs.bzl", "pgp_sign_checksums", "pgp_sign_detached")

pgp_sign_detached(
    name = "signed_tarball",
    src = ":tarball",
)

pgp_sign_checksums(
    name = "signed_checksums",
    srcs = [":tarball", ":package"],
)
```

```console
$ bazel build //:signed_tarball \
      --@envoy_toolshed//pgp:key_path=/run/user/1000/gpg/signing-key.asc#sha256=... \
      --@envoy_toolshed//pgp:passphrase_path=/run/user/1000/gpg/passphrase
```

Without the flags the build fails at analysis time:

```
No key path configured for //:signed_tarball.
```

**CI wiring recommendation:** A setup step writes the encrypted key and passphrase to `${runner.temp}/gpg/`, `chmod 600`, computes the key digest, and passes both flags to bazel; no `~/.gnupg`, no agent, no `HOME` mount required.

### Rules

| Rule | Purpose |
| --- | --- |
| `pgp_sign(name, src, mode, out, armor)` | Core rule. Signs a single `src`. `mode` is one of `detached`, `cleartext`, `inline` |
| `pgp_sign_detached(name, src, out)` | Detached, armored signature (`<src>.asc`) |
| `pgp_sign_cleartext(name, src, out)` | Cleartext signature - what `debsign` produces for `.changes`/`.dsc`, and what an apt `InRelease` is |
| `pgp_sign_checksums(name, srcs, algorithm, out)` | `shasum`-format checksums file for `srcs`, cleartext signed. Checksum generation is a separate, cacheable action - only signing handles secrets |
| `pgp_sign_changes_file(name, changes, out)` | Cleartext sign a Debian `.changes`/`.dsc` file itself. **Not** a full `debsign`: it does not sign referenced `.dsc`/`.buildinfo` files or rewrite their checksums - see the `TODO` on the rule |
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
       --key <abs-path-to-encrypted-secret-key> \
       [--key-sha256 <hex>] \
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

The intended toolshed approach for this is to build and publish a pinned,
static `sq` in the `bins-v*` release, the same way `sysroot`/`llvm_minimal`
are, so `pgp_ext.setup()` can work with no consumer-supplied sha256 - that is
a follow-up, not part of this rule set.

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

The audit is implemented as jq filters run by Starlark rules. The jq binary is
resolved from the hermetic `aspect_bazel_lib` jq toolchain; the audit never uses
host `jq` from `$PATH`.
The runnable `//pgp/audit:audit` likewise uses the toolchain jq via runfiles and
ignores any host `jq`.

For captured `bazel aquery --output=jsonproto` output, use `pgp_audit` to emit
a JSON report and `pgp_audit_test` to fail when the report has failures:

```starlark
load("@envoy_toolshed//pgp/audit:defs.bzl", "pgp_audit", "pgp_audit_test")

pgp_audit(
    name = "signing_audit_report",
    aquery = ":captured.json",
    forbidden_strings = ["known-forbidden-string"],
)

pgp_audit_test(
    name = "signing_audit_test",
    aquery = ":captured.json",
    forbidden_strings = ["known-forbidden-string"],
)
```

The report has the shape:

```json
{"actions": 1, "failures": [{"check": 1, "target": "//pkg:target", "detail": "..."}]}
```

It asserts that:

1. every `OpenPGPSign` action carries all of the required execution
   requirements,
2. no input reachable from an `OpenPGPSign` action (resolved transitively via
   `inputDepSetIds`) has a path matching
   `(^|/)\.gnupg(/|$)|private-keys-v1\.d|passphrase|secret|\.(asc|pgp|gpg|key)$`,
3. no `OpenPGPSign` action has `HOME`, `GNUPGHOME` or `SSH_AUTH_SOCK` in its
   environment,
4. no `OpenPGPSign` action passes a forbidden string (eg your passphrase) on
   the command line,
5. every `OpenPGPSign` action has exactly one non-tool input artifact (the file being signed).

For live use, either capture JSON yourself:

```console
$ bazel aquery --output=jsonproto "deps(//distribution:signed)" > aquery.json
$ bazel run @envoy_toolshed//pgp/audit:audit -- \
      --forbid "$(cat /run/user/1000/gpg/passphrase)" \
      --aquery-json "$PWD/aquery.json"
```

or let the runnable audit target invoke `bazel aquery` first:

```console
$ bazel run @envoy_toolshed//pgp/audit:audit -- \
      --forbid "$(cat /run/user/1000/gpg/passphrase)" \
      --@envoy_toolshed//pgp:key_path=/run/user/1000/gpg/signing-key.asc#sha256=... \
      --@envoy_toolshed//pgp:passphrase_path=/run/user/1000/gpg/passphrase \
      "deps(//distribution:signed)"
```

Any option other than `--forbid`/`--aquery-json` is passed through to
`bazel aquery`, so the targets can be audited in the configuration they are
actually built in.

Use `deps(...)` to audit the whole universe reachable from a target rather
than only the actions the target itself owns.

`//pgp/test:audit_test` runs the audit against captured `aquery` output
(`fixtures/audit.json`, the real output for the example targets in
`//pgp/test`) together with deliberately broken variants derived from it at
build time with the hermetic jq toolchain (a removed execution requirement, a
leaked environment variable, key material as an action input, a passphrase on
the command line), each of which the audit must reject.

`//pgp/test:live_audit` (`bazel run //pgp/test:live_audit`) is the live
counterpart: it re-invokes `bazel aquery` against the real dependency graph
of the same example targets, rather than captured JSON, so a regression that
only shows up in the real graph is caught too. It cannot run as a sandboxed
`bazel test` since it shells out to `bazel`.

## Alternative: signing after the build

The most conservative option remains signing *outside* the build graph:
`bazel build` produces the unsigned artifacts and a separate `bazel run`
target signs them on the host. Nothing that happens in `bazel run` is an
action, so nothing is hashed, cached or uploaded.

The toolchain here is deliberately reusable for that: the same signer binary
can be driven from a `bazel run` wrapper via the CLI contract above.
