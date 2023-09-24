load("//:versions.bzl", "VERSIONS")

json_data(
    name = "deps",
    data = VERSIONS,
)

jq(
    name = "dependency_versions",
    srcs = [":deps"],
    out = "dependency_shas.json",
    filter = """
    with_entries(select(.value | objects and .type == "github_archive") | .value |= {repo, sha256, url, version})
    """,
)
