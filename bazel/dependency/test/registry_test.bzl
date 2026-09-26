"""Tests for dependency registry updater rules."""

load("@bazel_skylib//lib:unittest.bzl", "analysistest", "asserts", "unittest")
load("//dependency:registry.bzl", "REGISTRY_RESOLVE_EXECUTION_REQUIREMENTS", "REGISTRY_RESOLVE_MNEMONIC", "REGISTRY_RESOLVE_TOOLCHAINS")
load("//git:defs.bzl", "GIT_TOOLCHAIN_TYPE")


def _registry_resolve_action(env):
    actions = [
        action
        for action in analysistest.target_actions(env)
        if action.mnemonic == REGISTRY_RESOLVE_MNEMONIC
    ]
    asserts.equals(env, 1, len(actions), "expected a single %s action" % REGISTRY_RESOLVE_MNEMONIC)
    return actions[0]


def _registry_resolve_action_test_impl(ctx):
    env = analysistest.begin(ctx)
    action = _registry_resolve_action(env)
    inputs = [f.basename for f in action.inputs.to_list()]
    argv = action.argv
    asserts.true(
        env,
        "git" in inputs,
        "expected hermetic git tool input, got %s" % inputs,
    )
    asserts.true(
        env,
        len([arg for arg in argv if arg.endswith("/bin/git")]) > 0,
        "expected git tool path in argv, got %s" % argv,
    )
    asserts.true(
        env,
        len([arg for arg in argv if arg.endswith("/resolved_toolchain")]) > 0,
        "expected jq tool path in argv, got %s" % argv,
    )
    return analysistest.end(env)


registry_resolve_action_test = analysistest.make(_registry_resolve_action_test_impl)


def _registry_resolve_runtime_inputs_test_impl(ctx):
    env = analysistest.begin(ctx)
    action = _registry_resolve_action(env)
    inputs = action.inputs.to_list()
    input_basenames = [f.basename for f in inputs]
    input_paths = [f.short_path for f in inputs]
    remote_helpers = [
        path
        for path in input_paths
        if path.endswith("/libexec/git-core/git-remote-https") or
           path.endswith("/libexec/git-core/git-remote-http")
    ]
    asserts.true(
        env,
        "ca-certificates.crt" in input_basenames,
        "expected CA bundle in action inputs, got %s" % input_paths,
    )
    asserts.true(
        env,
        len(remote_helpers) > 0,
        "expected git https helper in action inputs, got %s" % input_paths,
    )
    asserts.true(
        env,
        "registry.jq" in input_basenames,
        "expected registry jq inputs, got %s" % input_paths,
    )
    return analysistest.end(env)


registry_resolve_runtime_inputs_test = analysistest.make(_registry_resolve_runtime_inputs_test_impl)


def _registry_resolve_toolchain_test_impl(ctx):
    env = unittest.begin(ctx)
    asserts.equals(env, [GIT_TOOLCHAIN_TYPE], REGISTRY_RESOLVE_TOOLCHAINS)
    asserts.equals(env, "1", REGISTRY_RESOLVE_EXECUTION_REQUIREMENTS["requires-network"])
    asserts.equals(env, "1", REGISTRY_RESOLVE_EXECUTION_REQUIREMENTS["no-remote"])
    return unittest.end(env)


registry_resolve_toolchain_test = unittest.make(_registry_resolve_toolchain_test_impl)
