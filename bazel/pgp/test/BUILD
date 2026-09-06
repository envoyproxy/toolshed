load("@rules_shell//shell:sh_binary.bzl", "sh_binary")
load("@rules_shell//shell:sh_test.bzl", "sh_test")
load("//pgp:defs.bzl", "deb_sign_changes", "pgp_sign_checksums", "pgp_sign_cleartext", "pgp_sign_detached", "pgp_toolchain")
load(":sign_test.bzl", "args_test", "env_test", "execution_requirements_test", "no_passphrase_test", "relative_passphrase_test")

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

# Placeholder key/inputs. No key material is ever committed - the integration
# test generates a real (encrypted) key at test time.
genrule(
    name = "example_key",
    outs = ["example_key.pgp"],
    cmd = "echo 'NOT A KEY' > $@",
    tags = ["manual"],
)

genrule(
    name = "example_data",
    outs = ["example.txt"],
    cmd = "echo 'example' > $@",
    tags = ["manual"],
)

genrule(
    name = "example_changes",
    outs = ["example.changes"],
    cmd = "echo 'Format: 1.8' > $@",
    tags = ["manual"],
)

# Example signing targets. They are `manual` because building them requires
# `--@envoy_toolshed//pgp:passphrase_path` and a real signer toolchain.
pgp_sign_detached(
    name = "example_detached",
    src = "example.txt",
    key = "example_key.pgp",
    tags = ["manual"],
)

pgp_sign_cleartext(
    name = "example_cleartext",
    src = "example.txt",
    key = "example_key.pgp",
    out = "example.txt.cleartext.asc",
    tags = ["manual"],
)

pgp_sign_checksums(
    name = "example_checksums",
    srcs = [
        "example.changes",
        "example.txt",
    ],
    key = "example_key.pgp",
    tags = ["manual"],
)

deb_sign_changes(
    name = "example_deb_changes",
    changes = "example.changes",
    key = "example_key.pgp",
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

no_passphrase_test(
    name = "no_passphrase_test",
    target_under_test = ":example_detached",
)

relative_passphrase_test(
    name = "relative_passphrase_test",
    target_under_test = ":example_detached",
)

# Audits captured `bazel aquery` output, including deliberately broken
# fixtures which the audit script must reject.
#
# Run the same script against your own targets with:
#
#   bazel run //pgp/test:audit -- //your/targets/...
sh_test(
    name = "audit_test",
    size = "small",
    srcs = ["audit_fixtures_test.sh"],
    data = [
        "audit_test.sh",
        "@jq_toolchains//:resolved_toolchain",
    ] + glob(["fixtures/*.json"]),
    env = {
        "JQ_BIN": "$(JQ_BIN)",
    },
    toolchains = ["@jq_toolchains//:resolved_toolchain"],
)

sh_binary(
    name = "audit",
    srcs = ["audit_test.sh"],
    visibility = ["//visibility:public"],
)

# Signs with a real `sq`, if one is available (`SQ` or `$PATH`), and asserts
# that unencrypted keys are rejected. Skipped when `sq` is not installed.
sh_test(
    name = "signer_test",
    size = "medium",
    srcs = ["signer_test.sh"],
    data = ["//pgp/private:signer.sh"],
)
