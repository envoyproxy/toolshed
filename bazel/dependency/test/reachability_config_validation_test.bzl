load("@bazel_skylib//lib:unittest.bzl", "asserts", "unittest")
load("//dependency:reachability.bzl", "config_validation_error")

def _reachability_config_validation_test_impl(ctx):
    env = unittest.begin(ctx)

    message = config_validation_error(
        {"invalid": {"//dependency/test:reachability_mode": "extra"}},
        [],
    )
    asserts.equals(
        env,
        "Config 'invalid' varies '//dependency/test:reachability_mode' but it is not declared in flags. Declared flags: []",
        message,
    )

    message = config_validation_error(
        {"bare_key": {"wasm": "wasmtime"}},
        ["//dependency/test:reachability_mode"],
    )
    asserts.equals(
        env,
        (
            "Config 'bare_key' varies 'wasm', but config keys must be build setting labels " +
            "starting with '//', '@//' or '@@'. " +
            "Bazel does not support Starlark transitions on --define; use a build setting instead " +
            "(https://bazel.build/rules/config#user-defined-build-settings)."
        ),
        message,
    )

    message = config_validation_error(
        {"invalid_repo_form": {"@foo": "wasmtime"}},
        ["//dependency/test:reachability_mode"],
    )
    asserts.equals(
        env,
        (
            "Config 'invalid_repo_form' varies '@foo', but config keys must be build setting labels " +
            "starting with '//', '@//' or '@@'. " +
            "Bazel does not support Starlark transitions on --define; use a build setting instead " +
            "(https://bazel.build/rules/config#user-defined-build-settings)."
        ),
        message,
    )

    # A consumer in another repository must resolve its own flag labels, eg
    # `str(Label("//bazel:wasm_runtime"))`, because a bare `//` label in a .bzl
    # resolves against the repo defining it - the toolshed - rather than the
    # consumer's. Those resolved forms are apparent (`@//...`) or canonical
    # (`@@...`) and must be accepted.
    for resolved in ["@//bazel:wasm_runtime", "@@//bazel:wasm_runtime"]:
        asserts.equals(
            env,
            None,
            config_validation_error(
                {"v8": {resolved: "v8"}},
                [resolved],
            ),
        )

    # Repo-qualified labels are still matched against the declared flags.
    message = config_validation_error(
        {"v8": {"@//bazel:wasm_runtime": "v8"}},
        ["@//bazel:other_flag"],
    )
    asserts.equals(
        env,
        "Config 'v8' varies '@//bazel:wasm_runtime' but it is not declared in flags. Declared flags: [\"@//bazel:other_flag\"]",
        message,
    )

    return unittest.end(env)

reachability_config_validation_test = unittest.make(_reachability_config_validation_test_impl)
