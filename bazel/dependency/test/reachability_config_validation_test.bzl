load("@bazel_skylib//lib:unittest.bzl", "asserts", "unittest")
load("//dependency:reachability.bzl", "config_validation_error")

def _reachability_config_validation_test_impl(ctx):
    env = unittest.begin(ctx)

    message = config_validation_error(
        {"invalid": {"//dependency/test:reachability_mode": "extra"}},
        [],
        False,
    )
    asserts.equals(
        env,
        "Config 'invalid' varies '//dependency/test:reachability_mode' but it is not declared in flags. Declared flags: []",
        message,
    )

    message = config_validation_error(
        {"invalid_define": {"wasm": "wasmtime"}},
        ["//dependency/test:reachability_mode"],
        False,
    )
    asserts.equals(
        env,
        "Config 'invalid_define' varies define 'wasm' but this rule was constructed with defines = False",
        message,
    )

    return unittest.end(env)

reachability_config_validation_test = unittest.make(_reachability_config_validation_test_impl)
