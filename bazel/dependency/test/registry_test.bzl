"""Tests for dependency registry updater rules."""

load("@bazel_skylib//lib:unittest.bzl", "analysistest", "asserts", "unittest")
load("//dependency:registry.bzl", "REPO_REGISTRY_EXECUTION_REQUIREMENTS", "REPO_REGISTRY_MNEMONIC", "REPO_REGISTRY_TOOLCHAINS")
load("//git:defs.bzl", "GIT_TOOLCHAIN_TYPE")

def _repo_registry_action(env):
    actions = [
        action
        for action in analysistest.target_actions(env)
        if action.mnemonic == REPO_REGISTRY_MNEMONIC
    ]
    asserts.equals(env, 1, len(actions), "expected a single %s action" % REPO_REGISTRY_MNEMONIC)
    return actions[0]

def _repo_registry_action_test_impl(ctx):
    env = analysistest.begin(ctx)
    action = _repo_registry_action(env)
    inputs = [f.basename for f in action.inputs.to_list()]
    argv = action.argv
    asserts.true(
        env,
        "git" in inputs,
        "expected hermetic git tool input, got %s" % inputs,
    )
    asserts.true(
        env,
        argv[-1].endswith("/bin/git"),
        "expected git tool path in argv, got %s" % argv,
    )
    asserts.true(
        env,
        argv[-1].startswith("external/") or "/external/" in argv[-1],
        "expected hermetic git repo path in argv, got %s" % argv[-1],
    )
    return analysistest.end(env)

repo_registry_action_test = analysistest.make(_repo_registry_action_test_impl)

def _repo_registry_runtime_inputs_test_impl(ctx):
    env = analysistest.begin(ctx)
    action = _repo_registry_action(env)
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
    return analysistest.end(env)

repo_registry_runtime_inputs_test = analysistest.make(_repo_registry_runtime_inputs_test_impl)

def _repo_registry_toolchain_test_impl(ctx):
    env = unittest.begin(ctx)
    asserts.equals(env, [GIT_TOOLCHAIN_TYPE], REPO_REGISTRY_TOOLCHAINS)
    asserts.equals(env, "1", REPO_REGISTRY_EXECUTION_REQUIREMENTS["requires-network"])
    asserts.equals(env, "1", REPO_REGISTRY_EXECUTION_REQUIREMENTS["no-remote"])
    return unittest.end(env)

repo_registry_toolchain_test = unittest.make(_repo_registry_toolchain_test_impl)
