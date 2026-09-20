"""Public git toolchain surface."""

load("//git:toolchain.bzl", _GitInfo = "GitInfo", _git_toolchain = "git_toolchain")

GIT_TOOLCHAIN_TYPE = str(Label("@envoy_toolshed//git:toolchain_type"))
GitInfo = _GitInfo
git_toolchain = _git_toolchain
