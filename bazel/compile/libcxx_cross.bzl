"""Repository rules for cross-compilation libc++ libraries."""

load("//:versions.bzl", "VERSIONS")

# Maps target_arch to LLVM release triple used in tarball filenames
_ARCH_TO_TRIPLE = {
    "aarch64": "aarch64-linux-gnu",
    "x86_64": "x86_64-linux-gnu-ubuntu-18.04",
}

def _libcxx_cross_impl(ctx):
    """Implementation for libcxx_cross repository rule."""
    target_arch = ctx.attr.target_arch
    llvm_version = ctx.attr.llvm_version

    if target_arch not in _ARCH_TO_TRIPLE:
        fail("Unsupported target_arch: {}. Supported: {}".format(
            target_arch,
            list(_ARCH_TO_TRIPLE.keys()),
        ))

    triple = _ARCH_TO_TRIPLE[target_arch]
    lib_subdir = "{}-unknown-linux-gnu".format(target_arch)
    tarball_name = "clang+llvm-{}-{}.tar.xz".format(llvm_version, triple)
    strip_prefix = "clang+llvm-{}-{}".format(llvm_version, triple)

    url = "https://github.com/llvm/llvm-project/releases/download/llvmorg-{}/{}".format(
        llvm_version,
        tarball_name,
    )

    # Download the tarball
    ctx.download(
        url = url,
        output = tarball_name,
        sha256 = ctx.attr.sha256,
    )

    # Extract only the specific files we need from the large tarball.
    # --strip-components=1 removes the top-level "clang+llvm-{ver}-{triple}/" prefix,
    # leaving files at lib/{lib_subdir}/ and include/{lib_subdir}/c++/v1/.
    lib_files = [
        "{}/lib/{}/{}.a".format(strip_prefix, lib_subdir, lib)
        for lib in ["libc++", "libc++abi", "libunwind"]
    ]
    header_files = [
        "{}/include/{}/c++/v1/__config_site".format(strip_prefix, lib_subdir),
    ]

    result = ctx.execute(
        ["tar", "-xJf", tarball_name, "--strip-components=1"] + lib_files + header_files,
    )
    if result.return_code != 0:
        fail("Failed to extract files from {}: {}".format(tarball_name, result.stderr))

    # Remove the tarball to save disk space
    rm_result = ctx.execute(["rm", tarball_name])
    if rm_result.return_code != 0:
        # Non-fatal: log the failure but continue
        print("Warning: failed to remove tarball {}: {}".format(tarball_name, rm_result.stderr))

    # Create BUILD file
    ctx.file("BUILD.bazel", """package(default_visibility = ["//visibility:public"])

cc_library(
    name = "libcxx",
    srcs = ["lib/{lib_subdir}/libc++.a"],
    linkstatic = True,
    alwayslink = True,
)

cc_library(
    name = "libcxxabi",
    srcs = ["lib/{lib_subdir}/libc++abi.a"],
    linkstatic = True,
    alwayslink = True,
)

cc_library(
    name = "libunwind",
    srcs = ["lib/{lib_subdir}/libunwind.a"],
    linkstatic = True,
    alwayslink = True,
)

cc_library(
    name = "libcxx_cross",
    srcs = [
        "lib/{lib_subdir}/libc++.a",
        "lib/{lib_subdir}/libc++abi.a",
        "lib/{lib_subdir}/libunwind.a",
    ],
    linkstatic = True,
    alwayslink = True,
)

filegroup(
    name = "config_site_header",
    srcs = ["include/{lib_subdir}/c++/v1/__config_site"],
)
""".format(lib_subdir = lib_subdir))

libcxx_cross = repository_rule(
    implementation = _libcxx_cross_impl,
    attrs = {
        "target_arch": attr.string(
            mandatory = True,
            doc = "Target architecture (e.g., 'aarch64', 'x86_64')",
        ),
        "llvm_version": attr.string(
            mandatory = True,
            doc = "LLVM version to download (e.g., '18.1.8')",
        ),
        "sha256": attr.string(
            mandatory = True,
            doc = "SHA256 hash of the LLVM release tarball",
        ),
    },
    doc = "Downloads prebuilt libc++, libc++abi, and libunwind from LLVM release tarballs for cross-compilation",
)

def setup_libcxx_cross(
        target_arch = None,
        llvm_version = None,
        sha256 = None):
    """Setup function for WORKSPACE."""
    arch = target_arch or "aarch64"
    libcxx_cross(
        name = "libcxx_cross",
        target_arch = arch,
        llvm_version = llvm_version or VERSIONS["llvm"],
        sha256 = sha256 or VERSIONS["libcxx_cross_sha256"][arch],
    )
