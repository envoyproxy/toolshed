"""Low-level helpers for generated git source-toolchain repositories."""

load("//git:defs.bzl", _GIT_TOOLCHAIN_TYPE = "GIT_TOOLCHAIN_TYPE")
load("//git:toolchain.bzl", _git_toolchain = "git_toolchain")
load("//git/private:git_source.bzl", _git_source_wrapper_rule = "git_source_wrapper_rule")

GIT_TOOLCHAIN_TYPE = _GIT_TOOLCHAIN_TYPE
git_source_wrapper_rule = _git_source_wrapper_rule
git_toolchain = _git_toolchain
