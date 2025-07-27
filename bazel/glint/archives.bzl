"""Setup glint dependencies."""

load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive", "http_file")
load("//:versions.bzl", "VERSION_GLINT", "VERSIONS")

def _glint_archive(name, arch):
    """Create a glint archive repository."""
    # Map arch names to match what the workflow produces
    arch_map = {
        "x86_64": "amd64",
        "aarch64": "arm64",
    }
    release_arch = arch_map.get(arch, arch)

    # Download the binary directly (not a tar.xz)
    http_file(
        name = name,
        urls = ["https://github.com/envoyproxy/toolshed/releases/download/bazel-bins-v%s/glint-%s-%s" % (
            VERSIONS["bins_release"],
            VERSION_GLINT,
            release_arch,
        )],
        sha256 = VERSIONS.get("glint_%s_sha256" % release_arch, ""),  # Will be empty string until first release
        downloaded_file_path = "glint",
        executable = True,
    )

def setup_glint_archives():
    """Set up glint archives for supported architectures."""
    _glint_archive("glint_amd64", "x86_64")
    _glint_archive("glint_arm64", "aarch64")
