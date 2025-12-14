load("@bazel_features//:deps.bzl", "bazel_features_deps")
load("@rules_python//python:pip.bzl", "pip_parse")
load("//:versions.bzl", "VERSIONS")
load("//glint:glint_repository.bzl", "glint_repository")

def load_packages():
    # This is empty - it should be overridden in your repo
    pip_parse(
        name = "toolshed_pip3",
        requirements_lock = "@envoy_toolshed//:requirements.txt",
        python_interpreter_target = "@python3_12_host//:python",
    )
    bazel_features_deps()
    glint_repository(bins_release_version = VERSIONS["bins_release"])

def load_website_packages():
    # Only call this if you wish to use the website functionality
    pip_parse(
        name = "website_pip3",
        requirements_lock = "@envoy_toolshed//website:requirements.txt",
        python_interpreter_target = "@python3_12_host//:python",
    )
