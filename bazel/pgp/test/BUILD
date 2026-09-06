load("@aspect_bazel_lib//lib:jq.bzl", "jq")
load("@rules_shell//shell:sh_binary.bzl", "sh_binary")
load("@rules_shell//shell:sh_test.bzl", "sh_test")
load("//pgp/audit:defs.bzl", "pgp_audit_test")
load("//pgp:defs.bzl", "pgp_sign_changes_file", "pgp_sign_checksums", "pgp_sign_cleartext", "pgp_sign_detached", "pgp_toolchain")
load(":sign_test.bzl", "KEY_FRAGMENT_DIGEST", "args_test", "args_with_fragment_test", "bad_key_fragment_test", "env_test", "execution_requirements_test", "inputs_test", "no_key_test", "no_passphrase_test", "passphrase_fragment_test", "relative_key_test", "relative_passphrase_test")

# Stub signer/toolchain for the analysis tests. Real signing requires a
# registered `sq` toolchain, see //pgp:extensions.bzl.
sh_binary(
    name = "stub_signer",
    srcs = ["stub_signer.sh"],
)

pgp_toolchain(
    name = "stub_signer_toolchain",
    signer = ":stub_signer",
)

toolchain(
    name = "stub_toolchain",
    toolchain = ":stub_signer_toolchain",
    toolchain_type = "//pgp:toolchain_type",
)

# Example signing targets. They are `manual` because building them requires
# `--@envoy_toolshed//pgp:key_path`, `--@envoy_toolshed//pgp:passphrase_path`
# and a real signer toolchain.
pgp_sign_detached(
    name = "example_detached",
    src = "fixtures/example.txt",
    tags = ["manual"],
)

pgp_sign_cleartext(
    name = "example_cleartext",
    src = "fixtures/example.txt",
    out = "example.txt.cleartext.asc",
    tags = ["manual"],
)

pgp_sign_checksums(
    name = "example_checksums",
    srcs = [
        "fixtures/example.changes",
        "fixtures/example.txt",
    ],
    tags = ["manual"],
)

pgp_sign_changes_file(
    name = "example_deb_changes",
    changes = "fixtures/example.changes",
    tags = ["manual"],
)

execution_requirements_test(
    name = "execution_requirements_test",
)

env_test(
    name = "env_test",
    target_under_test = ":example_detached",
)

args_test(
    name = "detached_args_test",
    mode = "detached",
    target_under_test = ":example_detached",
)

args_with_fragment_test(
    name = "detached_args_with_fragment_test",
    expect_key_sha256 = KEY_FRAGMENT_DIGEST,
    mode = "detached",
    target_under_test = ":example_detached",
)

args_test(
    name = "cleartext_args_test",
    mode = "cleartext",
    target_under_test = ":example_cleartext",
)

args_test(
    name = "checksums_args_test",
    mode = "cleartext",
    target_under_test = ":example_checksums",
)

args_test(
    name = "deb_changes_args_test",
    mode = "cleartext",
    target_under_test = ":example_deb_changes",
)

inputs_test(
    name = "inputs_test",
    src = "fixtures/example.txt",
    target_under_test = ":example_detached",
)

no_key_test(
    name = "no_key_test",
    target_under_test = ":example_detached",
)

relative_key_test(
    name = "relative_key_test",
    target_under_test = ":example_detached",
)

bad_key_fragment_test(
    name = "bad_key_fragment_test",
    target_under_test = ":example_detached",
)

no_passphrase_test(
    name = "no_passphrase_test",
    target_under_test = ":example_detached",
)

relative_passphrase_test(
    name = "relative_passphrase_test",
    target_under_test = ":example_detached",
)

passphrase_fragment_test(
    name = "passphrase_fragment_test",
    target_under_test = ":example_detached",
)

PASSPHRASE = "correct-horse-battery-staple"

pgp_audit_test(
    name = "audit_test",
    aquery = "fixtures/audit.json",
)

jq(
    name = "audit_missing_exec_req",
    srcs = ["fixtures/audit.json"],
    filter_file = "fixtures/breakers/missing-exec-req.jq",
    out = "audit_missing_exec_req.json",
)

jq(
    name = "audit_env_leak",
    srcs = ["fixtures/audit.json"],
    filter_file = "fixtures/breakers/env-leak.jq",
    out = "audit_env_leak.json",
)

jq(
    name = "audit_passphrase_argv",
    srcs = ["fixtures/audit.json"],
    filter_file = "fixtures/breakers/passphrase-argv.jq",
    args = [
        "--arg",
        "passphrase",
        PASSPHRASE,
    ],
    out = "audit_passphrase_argv.json",
)

jq(
    name = "audit_key_material_input",
    srcs = ["fixtures/audit.json"],
    filter_file = "fixtures/breakers/key-material-input.jq",
    out = "audit_key_material_input.json",
)

jq(
    name = "audit_key_artifact_input",
    srcs = ["fixtures/audit.json"],
    filter_file = "fixtures/breakers/key-artifact-input.jq",
    out = "audit_key_artifact_input.json",
)

pgp_audit_test(
    name = "audit_missing_exec_req_test",
    aquery = ":audit_missing_exec_req",
    expect_failure = True,
)

pgp_audit_test(
    name = "audit_env_leak_test",
    aquery = ":audit_env_leak",
    expect_failure = True,
)

pgp_audit_test(
    name = "audit_passphrase_argv_test",
    aquery = ":audit_passphrase_argv",
    expect_failure = True,
    forbidden_strings = [PASSPHRASE],
)

pgp_audit_test(
    name = "audit_key_material_input_test",
    aquery = ":audit_key_material_input",
    expect_failure = True,
)

pgp_audit_test(
    name = "audit_key_artifact_input_test",
    aquery = ":audit_key_artifact_input",
    expect_failure = True,
)

# Runs the audit against a real `bazel aquery` of this package's example
# targets, rather than captured JSON (see `//pgp/test:audit_test` for that).
# `manual`: it shells out to `bazel`, so it cannot run as a sandboxed test -
# invoke explicitly with `bazel run //pgp/test:live_audit`, including in CI.
sh_binary(
    name = "live_audit",
    srcs = ["live_audit.sh"],
    tags = ["manual"],
)

# Signs with a real `sq`, if one is available (`SQ` or `$PATH`), and asserts
# that unencrypted keys are rejected. Skipped when `sq` is not installed.
sh_test(
    name = "signer_test",
    size = "medium",
    srcs = ["signer_test.sh"],
    data = ["//pgp/private:signer.sh"],
)
