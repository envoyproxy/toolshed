"""Public hunspell toolchain surface."""

load("//hunspell:toolchain.bzl", _HunspellInfo = "HunspellInfo", _hunspell_toolchain = "hunspell_toolchain")

HUNSPELL_TOOLCHAIN_TYPE = str(Label("@envoy_toolshed//hunspell:toolchain_type"))
HunspellInfo = _HunspellInfo
hunspell_toolchain = _hunspell_toolchain
