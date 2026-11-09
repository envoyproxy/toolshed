"""Repository rule exposing the jq modules needed by `//pgp/audit` and `//dependency/cve`."""

JQ_REPO_BUILD = """load(":defs.bzl", "jq_binary")

exports_files(glob(["**/*.jq"]) + ["defs.bzl", "launcher.sh.tpl", "modules_root.marker"])
filegroup(name = "modules", srcs = glob(["**/*.jq"]), visibility = ["//visibility:public"])

# jq with the modules importable: run it in place of jq.
jq_binary(name = "jq", visibility = ["//visibility:public"])
"""

def _jq_modules_repo_impl(ctx):
    files = {
        ctx.attr.aquery_module: "bazel/aquery.jq",
        ctx.attr.modules_root_marker: "modules_root.marker",
    }
    files.update(ctx.attr.files)
    directories = {}
    for path in files.values():
        if "/" in path:
            directories[path.rsplit("/", 1)[0]] = True
    for directory in directories:
        result = ctx.execute(["mkdir", "-p", directory])
        if result.return_code:
            fail("Failed to create jq modules repo directory: {}".format(result.stderr))
    for label, path in files.items():
        ctx.symlink(ctx.path(label), path)
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
        "files": attr.label_keyed_string_dict(
            allow_files = True,
            doc = "Further files to expose, mapped to their path in the repository.",
        ),
    },
    doc = "Creates the envoy_toolshed_jq repository used by //pgp/audit and //dependency/cve.",
)
