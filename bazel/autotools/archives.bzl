"""Setup autotools dependencies."""

load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive")
load("//:versions.bzl", "VERSIONS")

_AUTOTOOLS_BUILD_FILE = """
package(default_visibility = ["//visibility:public"])

filegroup(
    name = "all",
    srcs = glob(["**/*"]),
)

# Export all binaries 
exports_files(glob(["autotools-x86_64/bin/*", "autotools-aarch64/bin/*"]))

# Individual tool aliases
[alias(
    name = tool,
    actual = "autotools-x86_64/bin/" + tool,
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
"""

def _local_autotools_archive(name, tarball_path):
    """Create an autotools archive repository from a local tarball."""
    # Use http_archive with a file:// URL for local tarballs
    http_archive(
        name = name,
        urls = ["file://" + tarball_path],
        build_file_content = _AUTOTOOLS_BUILD_FILE,
    )

def _autotools_archive(name, arch):
    """Create an autotools archive repository from GitHub releases."""
    http_archive(
        name = name,
        urls = ["https://github.com/envoyproxy/toolshed/releases/download/bazel-bins-v%s/autotools-%s-%s-%s-%s-%s.tar.xz" % (
            VERSIONS["bins_release"],
            VERSIONS["m4"],
            VERSIONS["autoconf"],
            VERSIONS["automake"],
            VERSIONS["libtool"],
            arch
        )],
        sha256 = VERSIONS["autotools_%s_sha256" % arch],
        build_file_content = _AUTOTOOLS_BUILD_FILE,
    )

def setup_autotools_archives(local_tarball_path = None):
    """Set up autotools archives for both architectures.
    
    Args:
        local_tarball_path: Optional path to a local autotools tarball. If provided,
                           this will be used instead of downloading from GitHub releases.
                           The same tarball will be used for both architectures.
    """
    if local_tarball_path:
        # Use the same local tarball for both architectures
        _local_autotools_archive("autotools_x86_64", local_tarball_path)
        _local_autotools_archive("autotools_aarch64", local_tarball_path)
    else:
        # Download from GitHub releases
        _autotools_archive("autotools_x86_64", "x86_64")
        _autotools_archive("autotools_aarch64", "aarch64")
