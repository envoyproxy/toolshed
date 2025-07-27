load("@bazel_features//:deps.bzl", "bazel_features_deps")
load("@rules_python//python:pip.bzl", "pip_parse")
load("@rules_rust//crate_universe:defs.bzl", "crates_repository")
load("//:versions.bzl", "VERSIONS")

def load_packages():
    # This is empty - it should be overridden in your repo
    pip_parse(
        name = "toolshed_pip3",
        requirements_lock = "@envoy_toolshed//:requirements.txt",
        python_interpreter_target = "@python3_12_host//:python",
    )
    bazel_features_deps()

    # Rust crate dependencies for glint
    crates_repository(
        name = "crates",
        cargo_lockfile = "@envoy_toolshed//rust:Cargo.lock",
        manifests = [
            "@envoy_toolshed//rust:Cargo.toml",
            "@envoy_toolshed//rust/glint:Cargo.toml",
        ],
    )

def load_website_packages():
    # Only call this if you wish to use the website functionality
    pip_parse(
        name = "website_pip3",
        requirements_lock = "@envoy_toolshed//website:requirements.txt",
        python_interpreter_target = "@python3_12_host//:python",
    )
