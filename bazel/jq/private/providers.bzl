"""jq's staged module closure and shared toolchain identifier."""

JQ_TOOLCHAIN_TYPE = "@aspect_bazel_lib//lib:jq_toolchain_type"

JqInfo = provider(
    doc = "Staged jq module files and ordered import roots.",
    fields = {
        "transitive_srcs": "Depset of staged module trees containing all transitive .jq/.json files.",
        "roots": "Preorder depset of staged directories, direct library before dependencies.",
    },
)
