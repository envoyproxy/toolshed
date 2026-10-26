"""Public API for composable jq libraries, executables, and tests."""

load("//jq/private:binary.bzl", _jq_binary = "jq_binary")
load("//jq/private:library.bzl", _jq_library = "jq_library")
load("//jq/private:providers.bzl", _JQ_TOOLCHAIN_TYPE = "JQ_TOOLCHAIN_TYPE", _JqInfo = "JqInfo")
load("//jq/private:test.bzl", _jq_test = "jq_test")

JQ_TOOLCHAIN_TYPE = _JQ_TOOLCHAIN_TYPE
JqInfo = _JqInfo
jq_library = _jq_library
jq_binary = _jq_binary
jq_test = _jq_test
