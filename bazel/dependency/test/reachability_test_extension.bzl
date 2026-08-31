"""Test-only module extension for reachability tests."""

def _test_repo_impl(ctx):
    ctx.file("BUILD.bazel", ctx.attr.build_file_content)

_test_repo = repository_rule(
    implementation = _test_repo_impl,
    attrs = {
        "build_file_content": attr.string(mandatory = True),
    },
)

def _reachability_test_extension_impl(module_ctx):
    _test_repo(
        name = "apparent_excluded_transitive_repo",
        build_file_content = """\
package(default_visibility = ["//visibility:public"])

filegroup(
    name = "leaf",
    srcs = [],
)
""",
    )
    _test_repo(
        name = "apparent_excluded_repo",
        build_file_content = """\
package(default_visibility = ["//visibility:public"])

filegroup(
    name = "direct",
    srcs = ["@apparent_excluded_transitive_repo//:leaf"],
)
""",
    )

reachability_test_extension = module_extension(
    implementation = _reachability_test_extension_impl,
)
