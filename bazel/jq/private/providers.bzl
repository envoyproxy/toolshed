"""jq's staged module closure and shared toolchain identifier."""

JQ_TOOLCHAIN_TYPE = "@aspect_bazel_lib//lib:jq_toolchain_type"

JqInfo = provider(
    doc = "Original jq module sources and ordered staged import roots.",
    fields = {
        "transitive_srcs": "Depset of original, unstaged transitive .jq/.json source Files.",
        "roots": "Preorder depset of staged directories, direct library before dependencies.",
    },
)
