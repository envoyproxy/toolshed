load("@rules_pkg//:pkg.bzl", "pkg_tar")
load("@rules_python//python:py_binary.bzl", "py_binary")
load("@website_pip3//:requirements.bzl", "entry_point", "requirement")

# Note: pelican package contains test files with non-ASCII filenames (e.g., 'décembre')
# that cause build issues when using py_console_script_binary with pkg parameter.
# Instead, we use py_binary with entry_point() which doesn't include test data files.

alias(
    name = "pelican",
    actual = entry_point("pelican"),
    visibility = ["//visibility:public"],
)

alias(
    name = "pelican-quickstart",
    actual = entry_point("pelican-quickstart"),
)

alias(
    name = "pelican-themes",
    actual = entry_point("pelican-themes"),
)
