load("@bazel_skylib//lib:unittest.bzl", "asserts", "unittest")
load("//dependency:reachability.bzl", "apparent_name")

def _apparent_name_test_impl(ctx):
    env = unittest.begin(ctx)

    # WORKSPACE mode: canonical name is already the apparent name.
    asserts.equals(env, "boringssl", apparent_name("boringssl"))

    # bzlmod module repos (versionless canonical forms).
    asserts.equals(env, "rules_rust", apparent_name("rules_rust+"))
    asserts.equals(env, "rules_rust", apparent_name("rules_rust~"))

    # bzlmod extension-generated repos in any separator style.
    asserts.equals(env, "wasmtime", apparent_name("module++ext+wasmtime"))
    asserts.equals(env, "wasmtime", apparent_name("module~~ext~wasmtime"))
    asserts.equals(env, "wasmtime", apparent_name("+ext+wasmtime"))
    asserts.equals(env, "wasmtime", apparent_name("module+ext+wasmtime"))

    return unittest.end(env)

apparent_name_test = unittest.make(_apparent_name_test_impl)
