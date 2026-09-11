"""WORKSPACE repository setup for hermetic OpenPGP signing."""

load("//pgp/private:jq_repo.bzl", "jq_modules_repository")
load("//pgp/private:sq_repo.bzl", "sq_repository")

def setup_sq():
    """Creates the WORKSPACE repositories required by `//pgp`."""
    if "envoy_toolshed_jq" not in native.existing_rules():
        jq_modules_repository(
            name = "envoy_toolshed_jq",
            aquery_module = "@envoy_toolshed//jq:bazel/aquery.jq",
            modules_root_marker = "@envoy_toolshed//jq:modules_root.marker",
        )
    if "sq" not in native.existing_rules():
        sq_repository(
            name = "sq",
            linux_arm64_build = "@sq_linux_arm64//:BUILD.bazel",
            linux_x86_64_build = "@sq_linux_x86_64//:BUILD.bazel",
        )
