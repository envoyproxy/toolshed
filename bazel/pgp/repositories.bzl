"""WORKSPACE repository setup for hermetic OpenPGP signing."""

load("//pgp/private:jq_repo.bzl", "jq_modules_repository")
load("//pgp/private:sq_repo.bzl", "sq_repository")

# The `@envoy_toolshed//jq` files exposed as `@envoy_toolshed_jq`, besides the
# aquery module and the module root marker.
JQ_FILES = [
    "ansi.jq",
    "cve/cna_matcher.jq",
    "cve/matcher.jq",
    "cve/merge.jq",
    "cve/nvd_scan.jq",
    "cve/report.jq",
    "cve/utils.jq",
    "defs.bzl",
    "launcher.sh.tpl",
    "version.jq",
]

def setup_sq():
    """Creates the WORKSPACE repositories required by `//pgp` and `//dependency/cve`."""
    if "envoy_toolshed_jq" not in native.existing_rules():
        jq_modules_repository(
            name = "envoy_toolshed_jq",
            aquery_module = "@envoy_toolshed//jq:bazel/aquery.jq",
            modules_root_marker = "@envoy_toolshed//jq:modules_root.marker",
            files = {"@envoy_toolshed//jq:" + path: path for path in JQ_FILES},
        )
    if "sq" not in native.existing_rules():
        sq_repository(
            name = "sq",
            linux_arm64_build = "@sq_linux_arm64//:BUILD.bazel",
            linux_x86_64_build = "@sq_linux_x86_64//:BUILD.bazel",
        )
