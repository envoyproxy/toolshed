"""Test-only module extension for reachability tests."""

def _test_repo_impl(ctx):
    ctx.file("BUILD.bazel", ctx.attr.build_file_content)

_test_repo = repository_rule(
    implementation = _test_repo_impl,
    attrs = {
        "build_file_content": attr.string(mandatory = True),
    },
)

def reachability_test_repos():
    """Declares the fixture repos shared by bzlmod and WORKSPACE reachability tests."""
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

def _reachability_test_extension_impl(_module_ctx):
    reachability_test_repos()

reachability_test_extension = module_extension(
    implementation = _reachability_test_extension_impl,
)
