load("@rules_pkg//:pkg.bzl", "pkg_tar")
load("@rules_python//python/entry_points:py_console_script_binary.bzl", "py_console_script_binary")

py_console_script_binary(
    name = "pelican",
    pkg = "@website_pip3//pelican",
    script = "pelican",
    deps = [
        requirement("cssmin"),
        requirement("libsass"),
        requirement("markdown"),
        requirement("pelican-webassets"),
        requirement("packaging"),
        requirement("pyyaml"),
    ],
    entry_point_alias = pip_entry_point,
    visibility = ["//visibility:public"],
)

alias(
    name = "pelican-quickstart",
    actual = pip_entry_point(
        pkg = "pelican",
        script = "pelican-quickstart",
    ),
)

alias(
    name = "pelican-themes",
    actual = py_console_script_binary(
        pkg = "@website_pip3//pelican",
        script = "pelican-themes",
    ),
)
