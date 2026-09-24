"""Public git source-toolchain opt-in surface."""

load("//git:toolchain.bzl", _git_toolchain = "git_toolchain")
load("//git/private:git_source.bzl", _git_source_wrapper = "git_source_wrapper")

GIT_TOOLCHAIN_TYPE = str(Label("@envoy_toolshed//git:toolchain_type"))
git_source_wrapper = _git_source_wrapper
git_toolchain = _git_toolchain
