"""jq's staged module closure and shared toolchain identifier."""

# Canonical, so consumers can use it without their own `jq.bzl` mapping.
JQ_TOOLCHAIN_TYPE = str(Label("@jq.bzl//jq/toolchain:type"))

JqInfo = provider(
    doc = "Original jq module sources and ordered staged import roots.",
    fields = {
        "transitive_srcs": "Depset of original, unstaged transitive .jq/.json source Files.",
        "roots": "Preorder depset of staged `.jq_root` marker Files, each in its import root, direct library before dependencies.",
    },
)
