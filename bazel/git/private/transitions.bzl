"""Transitions shared by git packaging and toolchain setup."""

GIT_PLATFORMS = {
    "linux-x86_64": "@toolchains_llvm//platforms:linux-x86_64",
    "linux-aarch64": "@toolchains_llvm//platforms:linux-aarch64",
}

def _git_platform_transition_impl(_settings, attr):
    return {
        "//command_line_option:platforms": [GIT_PLATFORMS[attr.platform]],
        "@curl//:ssl_lib": "openssl",
    }

git_platform_transition = transition(
    implementation = _git_platform_transition_impl,
    inputs = [],
    outputs = [
        "//command_line_option:platforms",
        "@curl//:ssl_lib",
    ],
)

def _openssl_transition_impl(_settings, _attr):
    return {
        "@curl//:ssl_lib": "openssl",
    }

openssl_transition = transition(
    implementation = _openssl_transition_impl,
    inputs = [],
    outputs = ["@curl//:ssl_lib"],
)
