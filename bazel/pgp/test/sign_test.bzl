"""Analysis tests for the OpenPGP signing rules."""

load("@bazel_skylib//lib:unittest.bzl", "analysistest", "asserts", "unittest")
load("//pgp/private:sign.bzl", "EXECUTION_REQUIREMENTS", "MNEMONIC")

PASSPHRASE_PATH = "/tmp/envoy-toolshed-pgp-test/passphrase"

# Canonical label - `config_settings` keys are resolved in the repo mapping of
# bazel_skylib, so an apparent label would not resolve.
PASSPHRASE_FLAG = str(Label("//pgp:passphrase_path"))

# Execution requirements every signing action must carry. Listed here
# independently of the rule, so that dropping one from the rule fails this
# test. `//pgp/test:audit_test` additionally checks captured `aquery` output.
REQUIRED_EXECUTION_REQUIREMENTS = [
    "local",
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
    asserts.equals(env, {}, action.env, "%s action environment is not empty" % MNEMONIC)
    return analysistest.end(env)

env_test = analysistest.make(
    _env_test_impl,
    config_settings = {PASSPHRASE_FLAG: PASSPHRASE_PATH},
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
        "mode": attr.string(mandatory = True),
    },
    config_settings = {PASSPHRASE_FLAG: PASSPHRASE_PATH},
)

def _no_passphrase_test_impl(ctx):
    env = analysistest.begin(ctx)
    asserts.expect_failure(env, "No passphrase path configured")
    return analysistest.end(env)

no_passphrase_test = analysistest.make(
    _no_passphrase_test_impl,
    expect_failure = True,
    config_settings = {PASSPHRASE_FLAG: ""},
)

def _relative_passphrase_test_impl(ctx):
    env = analysistest.begin(ctx)
    asserts.expect_failure(env, "is not absolute")
    return analysistest.end(env)

relative_passphrase_test = analysistest.make(
    _relative_passphrase_test_impl,
    expect_failure = True,
    config_settings = {PASSPHRASE_FLAG: "passphrase"},
)
