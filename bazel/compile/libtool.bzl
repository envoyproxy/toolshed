"""Repository rule for downloading prebuilt libtool binaries."""

load("//:versions.bzl", "VERSIONS")

def _get_platform_arch(ctx):
    """Get the platform architecture for libtool selection."""
    arch = ctx.os.arch
    if arch == "x86_64" or arch == "amd64":
        return "x86_64"
    elif arch == "aarch64" or arch == "arm64":
        return "aarch64"
    else:
        fail("Unsupported architecture: {}".format(arch))

def _libtool_impl(ctx):
    """Implementation for libtool repository rule."""
    arch = ctx.attr.arch or _get_platform_arch(ctx)
    version = ctx.attr.version or VERSIONS["libtool"]
    sha256 = ctx.attr.sha256 or VERSIONS["libtool_%s_sha256" % arch]
    bins_version = ctx.attr.bins_version or VERSIONS["bins_release"]
    ctx.download_and_extract(
        url = "https://github.com/envoyproxy/toolshed/releases/download/bazel-bins-v{bins_version}/libtool-{version}-{arch}.tar.xz".format(
            bins_version = bins_verison,
            version = version,
            arch = arch,
        ),
        sha256 = sha256,
        stripPrefix = "libtool-{}".format(arch),
    )
    ctx.file("BUILD.bazel", """
package(default_visibility = ["//visibility:public"])

filegroup(
    name = "all",
    srcs = glob(["**"]),
)

filegroup(
    name = "libtoolize",
    srcs = ["bin/libtoolize"],
)

filegroup(
    name = "libtool",
    srcs = ["bin/libtool"],
)

filegroup(
    name = "m4_files",
    srcs = glob(["share/aclocal/*.m4"]),
)

filegroup(
    name = "share",
    srcs = glob(["share/**"]),
)
""")

libtool = repository_rule(
    implementation = _libtool_impl,
    attrs = {
        "version": attr.string(
            doc = "Version of libtool (e.g., '2.5.4')",
        ),
        "bins_version": attr.string(
            doc = "Version of toolshed bins release to download from",
        ),
        "sha256": attr.string(
            doc = "SHA256 hash of the libtool archive",
        ),
        "arch": attr.string(
            doc = "Architecture to download (x86_64 or aarch64). If not specified, uses host architecture",
        ),
    },
    doc = "Downloads prebuilt libtool for the specified or host architecture",
)

def setup_libtool(version = None, bins_version = None, sha256 = None, arch = None):
    libtool(
        version = version or VERSIONS["libtool"],
        bins_version = bins_version or VERSIONS["bins_version"],
        sha256 = sha256 or VERSIONS["sha256"],
        arch = arch,
    )
