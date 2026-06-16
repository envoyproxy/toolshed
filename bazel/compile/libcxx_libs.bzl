"""Repository rules for prebuilt libcxx bundles for cross-compilation."""

load("//:versions.bzl", "VERSIONS")

def _libcxx_libs_impl(ctx):
    """Implementation for libcxx libs repository rule."""
    arch = ctx.attr.arch
    ctx.download_and_extract(
        url = "https://github.com/envoyproxy/toolshed/releases/download/bins-v{version}/libcxx-llvm{llvm_version}-{arch}.tar.xz".format(
            arch = arch,
            version = ctx.attr.version,
            llvm_version = VERSIONS["llvm"],
        ),
        sha256 = ctx.attr.sha256,
    )

    # Create BUILD file
    ctx.file("BUILD.bazel", """
package(default_visibility = ["//visibility:public"])

filegroup(
    name = "libcxx_libs_{arch}",
    srcs = glob(["include/**", "lib/**"]),
)

filegroup(
    name = "headers",
    srcs = glob(["include/**"]),
)

filegroup(
    name = "libs",
    srcs = glob(["lib/**"]),
)

""".format(arch = arch))

libcxx_libs = repository_rule(
    implementation = _libcxx_libs_impl,
    attrs = {
        "version": attr.string(
            mandatory = True,
            doc = "Release version to download (e.g., '0.1.46')",
        ),
        "sha256": attr.string(
            mandatory = True,
            doc = "SHA256 hash of the libcxx libs archive",
        ),
        "arch": attr.string(
            mandatory = True,
            doc = "Architecture to target (aarch64 or x86_64)",
            values = ["aarch64", "x86_64"],
        ),
    },
    doc = "Downloads prebuilt libcxx bundles for cross-compilation with toolchains_llvm",
)

def _libcxx_libs_darwin_impl(ctx):
    """Implementation for darwin libcxx libs repository rule."""
    arch = ctx.attr.arch

    sha256 = ctx.attr.sha256
    if sha256:
        ctx.download_and_extract(
            url = "https://github.com/envoyproxy/toolshed/releases/download/bins-v{version}/libcxx-llvm{llvm_version}-darwin-{arch}.tar.xz".format(
                arch = arch,
                version = ctx.attr.version,
                llvm_version = VERSIONS["llvm"],
            ),
            sha256 = sha256,
        )
    else:
        # No hash available yet — generate __config_site from the Linux version.
        ctx.execute(["mkdir", "-p", "include", "lib"])
        linux_config_site = ctx.path(Label("@llvm_toolchain_llvm//:include/x86_64-unknown-linux-gnu/c++/v1/__config_site"))
        ctx.execute(["cp", str(linux_config_site), "include/__config_site"])

    ctx.file("BUILD.bazel", """
package(default_visibility = ["//visibility:public"])

filegroup(
    name = "libcxx_libs_darwin_{arch}",
    srcs = glob(["include/**", "lib/**"]),
)

filegroup(
    name = "headers",
    srcs = glob(["include/**"]),
)

filegroup(
    name = "libs",
    srcs = glob(["lib/**"]),
)

""".format(arch = arch))

libcxx_libs_darwin = repository_rule(
    implementation = _libcxx_libs_darwin_impl,
    attrs = {
        "version": attr.string(
            mandatory = True,
            doc = "Release version to download",
        ),
        "sha256": attr.string(
            default = "",
            doc = "SHA256 hash of the darwin libcxx archive. Empty string generates a fallback __config_site.",
        ),
        "arch": attr.string(
            mandatory = True,
            doc = "Architecture (aarch64)",
            values = ["aarch64"],
        ),
    },
    doc = "Downloads prebuilt darwin libcxx for cross-compilation with toolchains_llvm",
)

def setup_libcxx_libs_darwin(
        aarch64_version = None,
        aarch64_sha256 = None):
    """Setup function for WORKSPACE.

    Creates @libcxx_libs_darwin_aarch64 repository.
    """
    sha256 = aarch64_sha256 or VERSIONS.get("libcxx_libs_darwin_sha256", {}).get("aarch64", "")
    if "libcxx_libs_darwin_aarch64" not in native.existing_rules():
        libcxx_libs_darwin(
            name = "libcxx_libs_darwin_aarch64",
            version = aarch64_version or VERSIONS["bins_release"],
            sha256 = sha256,
            arch = "aarch64",
        )

def setup_libcxx_libs(
        aarch64_version = None,
        aarch64_sha256 = None,
        x86_64_version = None,
        x86_64_sha256 = None):
    """Setup function for WORKSPACE.

    Creates @libcxx_libs_aarch64 and @libcxx_libs_x86_64 repositories.
    """
    libcxx_libs(
        name = "libcxx_libs_aarch64",
        version = aarch64_version or VERSIONS["bins_release"],
        sha256 = aarch64_sha256 or VERSIONS["libcxx_libs_sha256"]["aarch64"],
        arch = "aarch64",
    )

    libcxx_libs(
        name = "libcxx_libs_x86_64",
        version = x86_64_version or VERSIONS["bins_release"],
        sha256 = x86_64_sha256 or VERSIONS["libcxx_libs_sha256"]["x86_64"],
        arch = "x86_64",
    )
