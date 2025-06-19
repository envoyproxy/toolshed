"""Repository rule for autotools toolchain."""

def _autotools_repo_impl(ctx):
    ctx.file("BUILD.bazel", """
load("@{toolshed}//toolchains/autotools:current_toolchain.bzl", "current_autotools_toolchain")

# The main target that users reference
current_autotools_toolchain(
    name = "current_toolchain",
    visibility = ["//visibility:public"],
)

# Alias for convenience
alias(
    name = "toolchain",
    actual = ":current_toolchain",
    visibility = ["//visibility:public"],
)
""".format(toolshed = ctx.attr.toolshed_name))

autotools_repo = repository_rule(
    implementation = _autotools_repo_impl,
    attrs = {
        "toolshed_name": attr.string(
            default = "envoy_toolshed",
            doc = "Name of the toolshed repository",
        ),
    },
)

def setup_autotools_repo(name = "autotools", toolshed_name = "envoy_toolshed"):
    """Set up the autotools repository.

    Args:
        name: Repository name (default: "autotools")
        toolshed_name: Name of the toolshed repository (default: "envoy_toolshed")
    """
    autotools_repo(
        name = name,
        toolshed_name = toolshed_name,
    )
