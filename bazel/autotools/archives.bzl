"""Setup autotools dependencies."""

load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive")
load("//:versions.bzl", "VERSIONS")

def _autotools_archive(name, arch):
    """Create an autotools archive repository."""
    http_archive(
        name = name,
        urls = ["https://github.com/envoyproxy/toolshed/releases/download/bazel-bins-v0.1.11/autotools-%s-%s-%s-%s-%s.tar.xz" % (
            VERSIONS["m4"],
            VERSIONS["autoconf"],
            VERSIONS["automake"],
            VERSIONS["libtool"],
            arch
        )],
        sha256 = VERSIONS["autotools_%s_sha256" % arch],
        build_file_content = """
package(default_visibility = ["//visibility:public"])

filegroup(
    name = "all",
    srcs = glob(["**/*"]),
)

# Export all binaries
exports_files(glob(["bin/*"]))

# Individual tool aliases
[alias(
    name = tool,
    actual = "bin/" + tool,
) for tool in [
    "m4",
    "autoconf",
    "autoheader",
    "autoreconf",
    "autoscan",
    "autom4te",
    "autoupdate",
    "ifnames",
    "automake",
    "aclocal",
    "libtool",
    "libtoolize",
]]
""",
    )

def setup_autotools_archives():
    """Set up autotools archives for both architectures."""
    _autotools_archive("autotools_x86_64", "x86_64")
    _autotools_archive("autotools_aarch64", "aarch64")
