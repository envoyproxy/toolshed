"""Analysis tests for the OpenPGP signing rules."""

load("@bazel_skylib//lib:unittest.bzl", "analysistest", "asserts", "unittest")
load("//pgp/private:sign.bzl", "EXECUTION_REQUIREMENTS", "MNEMONIC")

KEY_PATH = "/tmp/envoy-toolshed-pgp-test/key.pgp"
KEY_PATH_WITH_FRAGMENT = "/tmp/envoy-toolshed-pgp-test/key.pgp#sha256=0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
KEY_FRAGMENT_DIGEST = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
PASSPHRASE_PATH = "/tmp/envoy-toolshed-pgp-test/passphrase"

# Canonical labels - `config_settings` keys are resolved in the repo mapping of
# bazel_skylib, so an apparent label would not resolve.
KEY_FLAG = str(Label("//pgp:key_path"))
PASSPHRASE_FLAG = str(Label("//pgp:passphrase_path"))

# Execution requirements every signing action must carry. Listed here
# independently of the rule, so that dropping one from the rule fails this
# test. `//pgp/test:audit_test` additionally checks captured `aquery` output.
REQUIRED_EXECUTION_REQUIREMENTS = [
    "no-cache",
    "no-remote",
    "no-remote-cache",
    "no-remote-cache-upload",
    "no-remote-exec",
]

# Environment variables that must never reach a signing action.
_FORBIDDEN_ENV = [
    "GNUPGHOME",
    "HOME",
    "SSH_AUTH_SOCK",
]

def _sign_action(env):
    actions = [
        action
        for action in analysistest.target_actions(env)
        if action.mnemonic == MNEMONIC
    ]
    asserts.equals(env, 1, len(actions), "expected a single %s action" % MNEMONIC)
    return actions[0]

def _execution_requirements_test_impl(ctx):
    env = unittest.begin(ctx)
    for requirement in REQUIRED_EXECUTION_REQUIREMENTS:
        asserts.true(
            env,
            requirement in EXECUTION_REQUIREMENTS,
            "signing actions are missing execution requirement `%s`" % requirement,
        )
    return unittest.end(env)

execution_requirements_test = unittest.make(_execution_requirements_test_impl)

def _env_test_impl(ctx):
    env = analysistest.begin(ctx)
    action = _sign_action(env)
    for name in _FORBIDDEN_ENV:
        asserts.true(
            env,
            name not in action.env,
            "%s action leaks `%s` into its environment" % (MNEMONIC, name),
        )
    asserts.equals(
        env,
        {"PATH": "/usr/bin:/bin"},
        action.env,
        "%s action environment is not the expected minimal PATH" % MNEMONIC,
    )
    return analysistest.end(env)

env_test = analysistest.make(
    _env_test_impl,
    config_settings = {
        KEY_FLAG: KEY_PATH,
        PASSPHRASE_FLAG: PASSPHRASE_PATH,
    },
)

def _args_test_impl(ctx):
    env = analysistest.begin(ctx)
    action = _sign_action(env)
    argv = action.argv
    asserts.true(
        env,
        "--require-encrypted-key" in argv,
        "%s action does not require an encrypted key" % MNEMONIC,
    )
    asserts.true(
        env,
        "--passphrase-file" in argv,
        "%s action does not pass a passphrase file" % MNEMONIC,
    )
    asserts.true(
        env,
        PASSPHRASE_PATH in argv,
        "%s action does not pass the configured passphrase path" % MNEMONIC,
    )
    asserts.true(
        env,
        "--key" in argv,
        "%s action does not pass a key path" % MNEMONIC,
    )
    asserts.equals(
        env,
        KEY_PATH,
        argv[argv.index("--key") + 1],
        "%s action does not pass the configured key path" % MNEMONIC,
    )
    if ctx.attr.expect_key_sha256:
        asserts.true(
            env,
            "--key-sha256" in argv,
            "%s action expected --key-sha256" % MNEMONIC,
        )
        asserts.equals(
            env,
            ctx.attr.expect_key_sha256,
            argv[argv.index("--key-sha256") + 1],
            "%s action passed wrong key sha256" % MNEMONIC,
        )
    else:
        asserts.false(
            env,
            "--key-sha256" in argv,
            "%s action should not pass --key-sha256 when no fragment is configured" % MNEMONIC,
        )
    asserts.equals(
        env,
        ctx.attr.mode,
        argv[argv.index("--mode") + 1],
        "%s action signs in the wrong mode" % MNEMONIC,
    )
    return analysistest.end(env)

args_test = analysistest.make(
    _args_test_impl,
    attrs = {
        "expect_key_sha256": attr.string(),
        "mode": attr.string(mandatory = True),
    },
    config_settings = {
        KEY_FLAG: KEY_PATH,
        PASSPHRASE_FLAG: PASSPHRASE_PATH,
    },
)

args_with_fragment_test = analysistest.make(
    _args_test_impl,
    attrs = {
        "expect_key_sha256": attr.string(),
        "mode": attr.string(mandatory = True),
    },
    config_settings = {
        KEY_FLAG: KEY_PATH_WITH_FRAGMENT,
        PASSPHRASE_FLAG: PASSPHRASE_PATH,
    },
)

def _inputs_test_impl(ctx):
    env = analysistest.begin(ctx)
    action = _sign_action(env)
    inputs = [f.short_path for f in action.inputs.to_list()]
    src_short_path = ctx.file.src.short_path
    signer = ctx.attr.signer[DefaultInfo].files_to_run.executable
    tool_inputs = {
        f.short_path: True
        for f in ctx.attr.signer[DefaultInfo].default_runfiles.files.to_list()
    }
    if signer:
        tool_inputs[signer.short_path] = True
    asserts.true(
        env,
        src_short_path in inputs,
        "expected %s in action inputs: %s" % (src_short_path, inputs),
    )
    non_tool_inputs = [f for f in inputs if f not in tool_inputs]
    asserts.equals(
        env,
        [src_short_path],
        non_tool_inputs,
        "signing action inputs must contain exactly src and tool files (no key): got %s" % inputs,
    )
    return analysistest.end(env)

inputs_test = analysistest.make(
    _inputs_test_impl,
    attrs = {
        "signer": attr.label(default = ":stub_signer"),
        "src": attr.label(mandatory = True, allow_single_file = True),
    },
    config_settings = {
        KEY_FLAG: KEY_PATH,
        PASSPHRASE_FLAG: PASSPHRASE_PATH,
    },
)

def _no_key_test_impl(ctx):
    env = analysistest.begin(ctx)
    asserts.expect_failure(env, "No key path configured")
    return analysistest.end(env)

no_key_test = analysistest.make(
    _no_key_test_impl,
    expect_failure = True,
    config_settings = {
        KEY_FLAG: "",
        PASSPHRASE_FLAG: PASSPHRASE_PATH,
    },
)

def _relative_key_test_impl(ctx):
    env = analysistest.begin(ctx)
    asserts.expect_failure(env, "is not absolute")
    return analysistest.end(env)

relative_key_test = analysistest.make(
    _relative_key_test_impl,
    expect_failure = True,
    config_settings = {
        KEY_FLAG: "relative/key.pgp",
        PASSPHRASE_FLAG: PASSPHRASE_PATH,
    },
)

def _bad_key_fragment_test_impl(ctx):
    env = analysistest.begin(ctx)
    asserts.expect_failure(env, "Invalid sha256 fragment")
    return analysistest.end(env)

bad_key_fragment_test = analysistest.make(
    _bad_key_fragment_test_impl,
    expect_failure = True,
    config_settings = {
        KEY_FLAG: "/tmp/key#md5=1234",
        PASSPHRASE_FLAG: PASSPHRASE_PATH,
    },
)

def _no_passphrase_test_impl(ctx):
    env = analysistest.begin(ctx)
    asserts.expect_failure(env, "No passphrase path configured")
    return analysistest.end(env)

no_passphrase_test = analysistest.make(
    _no_passphrase_test_impl,
    expect_failure = True,
    config_settings = {
        KEY_FLAG: KEY_PATH,
        PASSPHRASE_FLAG: "",
    },
)

def _relative_passphrase_test_impl(ctx):
    env = analysistest.begin(ctx)
    asserts.expect_failure(env, "is not absolute")
    return analysistest.end(env)

relative_passphrase_test = analysistest.make(
    _relative_passphrase_test_impl,
    expect_failure = True,
    config_settings = {
        KEY_FLAG: KEY_PATH,
        PASSPHRASE_FLAG: "passphrase",
    },
)

def _passphrase_fragment_test_impl(ctx):
    env = analysistest.begin(ctx)
    asserts.expect_failure(env, "passphrase digest is an oracle")
    return analysistest.end(env)

passphrase_fragment_test = analysistest.make(
    _passphrase_fragment_test_impl,
    expect_failure = True,
    config_settings = {
        KEY_FLAG: KEY_PATH,
        PASSPHRASE_FLAG: "/tmp/passphrase#sha256=0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
    },
)
