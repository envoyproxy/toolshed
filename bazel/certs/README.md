# Test certificate generator

`//certs:gen` produces X.509 test fixtures (certificates, CRLs, PKCS#12
bundles, OCSP responses and SPIFFE trust bundles) from a declarative spec
file. It replaces OpenSSL-CLI based fixture scripts that used to shell out to
the `openssl` CLI (and, sometimes, to `faketime`) to produce and refresh
checked-in test fixtures.

It links BoringSSL directly, so the fixtures it emits do not depend on any
TLS provider configuration in the consuming workspace.

## Usage

Load `generated_certs` and declare a target per spec file:

```starlark
load("@envoy_toolshed//certs:certs.bzl", "generated_certs")

generated_certs(
    name = "certs",
    spec = "certs.spec",
    srcs = glob(["*.cfg", "*_key.pem"]),
    outs = [
        "ca_cert.pem",
        "server_cert.pem",
        # ... every file the spec asks the generator to write.
    ],
    static_srcs = [
        # Any checked-in fixtures that live alongside the generated ones.
    ],
    headers_name = "certs_headers",
)
```

```console
$ bazel build //path/to:certs
$ ls bazel-bin/path/to/
```

Consumers depend on the resulting filegroup via `data = ["//path/to:certs"]`.
Generated or checked-in headers such as `*_cert_info.h` and `*_cert_hash.h`
are not included in that runtime filegroup. They are compile-time inputs and
should be referenced from `hdrs = [...]`. Generated headers can be referenced
directly or via an opt-in `headers_name` filegroup such as `:certs_headers`;
checked-in headers from `static_srcs` should be referenced directly.

## Year stamping

Certificates are valid from Jan 1 of a given year, so they never age out.

By default, `generated_certs` reads the year from `@cert_epoch//:year`. That
repo holds the host's current UTC year when it is fetched, so the year is a
regular, content-addressed input: the generator only reruns (and everything
built from its outputs is only rebuilt) when the year changes, or the
generator, spec or sources do. Stamping is not used, as the workspace status
files change on every build and would bust the cache each time. No consumer
configuration is required.

To pin the year:

- `--repo_env=CERT_EPOCH_YEAR=<YYYY>` sets it for every `generated_certs`
  target;
- `year = <YYYY>` pins it for one target;
- `year_file = "<label>"` reads it from another file holding the year.

The repo is not refetched automatically, so a long-lived local output base
keeps the year it first fetched. `current` fixtures expire on Jan 1 of the
epoch year + 2 (eg an epoch fetched in December 2026 expires in January 2028),
so refetch it before then, eg with `bazel clean --expunge` or by setting
`CERT_EPOCH_YEAR`. CI runners that start from a fresh output base always fetch
the current year.

Three validity modes are available:

| Mode | notBefore | notAfter |
| --- | --- | --- |
| `current` (default) | Jan 1 of the epoch year | +2 years |
| `expired` | Jan 1 2020 | Jan 1 2021 |
| `long` | Jan 1 of the epoch year | +18250 days |

Serial numbers are derived from a hash of the fixture name (or pinned in the
spec), never randomly, so CRL and OCSP entries stay consistent and repeated
builds are byte-identical for RSA fixtures.

## Spec format

An INI-like file. Each stanza is `[<kind> <name>]` followed by `key = value`
lines. Keys may repeat where noted. Blank lines and `#` comments are ignored.

### `[cert <name>]`

| Key | Meaning |
| --- | --- |
| `key` | private key file, relative to `--in-dir` (required) |
| `key_password` | password for an encrypted key |
| `cfg` | OpenSSL config supplying the subject and extensions (required) |
| `section` | config section holding the v3 extensions (default `v3_ca`) |
| `subject_section` | config section holding the subject (default `req_distinguished_name`) |
| `issuer` | name of the issuing fixture, or `self` (default `self`) |
| `validity` | `current`, `expired` or `long` (default `current`) |
| `serial` | pinned serial in hex; derived from the name if absent |
| `out` | output file name (default `<name>_cert.pem`); `none` suppresses it |
| `info_header` | emit a `*_cert_info.h` header with this name |
| `hash_header` | emit a `*_cert_hash.h` header with this name |

If the extension section is missing from the config, the certificate is emitted
as X.509 v1, matching what `openssl ca` used to do.

### `[concat <output>]`

`parts` is a comma-separated list of fixture names and/or previously written
output files, concatenated in order.

### `[crl <output>]`

`issuer` names the signing CA; `revoke` is a comma-separated list of fixtures
whose serials are revoked.

### `[p12 <output>]`

`cert` names the fixture whose certificate and key are bundled. `chain` adds
extra certificates. `password` or `password_file` set the passphrase, and
`encrypt = none` disables key/certificate encryption and MAC iteration.

### `[ocsp <output>]`

RFC 6960 responses, encoded by hand because BoringSSL has no OCSP module.
`cert`, `issuer` and `status` may repeat (once per SingleResponse).
`responder` names the signing fixture, `responder_id` is `name` or `key`, and
`next_update_days` adds a nextUpdate field. `info_header` emits the thisUpdate
and nextUpdate timestamps as constants.

### `[trust_bundle <output>]`

`domain` may repeat; each entry is `<trust domain>:<cert>[+<cert>...]:<sequence
number>` and produces a SPIFFE trust bundle entry.

## Testing

Run the hermetic generator tests from the Bazel module root:

```console
$ bazel test //certs/...
```

The tests generate all supported output kinds, check their structure without
calling the host OpenSSL binary, and exercise malformed specifications.

Note that `.spec` files are commonly gitignored (the PyInstaller rule matches
the same extension), so the root `.gitignore` carves out an exception for
`bazel/certs/**/*.spec` to keep this package's spec fixtures tracked.
