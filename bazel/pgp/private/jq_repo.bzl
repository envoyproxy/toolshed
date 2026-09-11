"""Repository rule exposing the jq modules needed by `//pgp/audit`."""

JQ_REPO_BUILD = """exports_files(glob(["**/*.jq"]) + ["modules_root.marker"])
filegroup(name = "modules", srcs = glob(["**/*.jq"]), visibility = ["//visibility:public"])
"""

def _jq_modules_repo_impl(ctx):
    result = ctx.execute(["mkdir", "-p", "bazel"])
    if result.return_code:
        fail("Failed to create jq modules repo directory: {}".format(result.stderr))
    ctx.symlink(ctx.path(ctx.attr.aquery_module), "bazel/aquery.jq")
    ctx.symlink(ctx.path(ctx.attr.modules_root_marker), "modules_root.marker")
    ctx.file("BUILD.bazel", JQ_REPO_BUILD)

jq_modules_repository = repository_rule(
    implementation = _jq_modules_repo_impl,
    attrs = {
        "aquery_module": attr.label(
            mandatory = True,
            allow_single_file = True,
            doc = "The aquery jq module file to expose.",
        ),
        "modules_root_marker": attr.label(
            mandatory = True,
            allow_single_file = True,
            doc = "Marker file identifying the jq module root.",
        ),
    },
    doc = "Creates the envoy_toolshed_jq repository used by //pgp/audit.",
)
