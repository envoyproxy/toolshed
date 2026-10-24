"""Analysis-only tests: never execute the network fetch action."""

load("@bazel_skylib//lib:unittest.bzl", "analysistest", "asserts")

def _fetch_action_test_impl(ctx):
    env = analysistest.begin(ctx)
    actions = [a for a in analysistest.target_actions(env) if a.mnemonic == "CveFetch"]
    asserts.equals(env, 1, len(actions))
    action = actions[0]
    asserts.equals(env, "fixture-refresh", action.env.get("CVE_UPDATE_NONCE"))
    asserts.true(env, action.outputs.to_list()[0].is_directory)
    inputs = [f.short_path for f in action.inputs.to_list()]
    asserts.true(env, any([p.endswith("cve_data/2024-01.json") for p in inputs]))
    return analysistest.end(env)

fetch_action_test = analysistest.make(
    _fetch_action_test_impl,
    config_settings = {
        "//command_line_option:action_env": ["CVE_UPDATE_NONCE=fixture-refresh"],
    },
)

def _update_analysis_test_impl(ctx):
    env = analysistest.begin(ctx)
    target = analysistest.target_under_test(env)
    asserts.true(env, target[DefaultInfo].files_to_run.executable != None)
    return analysistest.end(env)

update_analysis_test = analysistest.make(_update_analysis_test_impl)
