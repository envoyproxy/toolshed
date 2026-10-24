"""Repository rule for shared LLVM libunwind built against the toolshed sysroot."""

load("//:versions.bzl", "VERSIONS")

def _unwind_libs_impl(ctx):
    arch = ctx.attr.arch
    if arch != "x86_64":
        fail("Compilation for non-x86_64 architectures not yet implemented")
    if not ctx.attr.sha256:
        fail("SHA256 hash not yet available for shared libunwind on {}. This configuration may not be released yet.".format(arch))

    ctx.download_and_extract(
        url = "https://github.com/envoyproxy/toolshed/releases/download/bins-v{version}/unwind-llvm{llvm_version}-{arch}.tar.xz".format(
            arch = arch,
            version = ctx.attr.version,
            llvm_version = VERSIONS["llvm"],
        ),
        sha256 = ctx.attr.sha256,
        stripPrefix = "unwind-libs-{}".format(arch),
    )
    ctx.file("BUILD.bazel", """
load("@rules_cc//cc:defs.bzl", "cc_import")

package(default_visibility = ["//visibility:public"])

filegroup(
    name = "libunwind_so",
    srcs = ["lib/libunwind.so.1"],
)

cc_import(
    name = "libunwind",
    shared_library = "lib/libunwind.so.1",
)
""")

unwind_libs = repository_rule(
    implementation = _unwind_libs_impl,
    attrs = {
        "version": attr.string(
            mandatory = True,
            doc = "Release version to download (e.g., '1.0.0')",
        ),
        "sha256": attr.string(
            mandatory = True,
            doc = "SHA256 hash of the shared libunwind archive",
        ),
        "arch": attr.string(
            default = "x86_64",
            doc = "Architecture to target",
        ),
    },
    doc = "Downloads shared LLVM libunwind built against the toolshed sysroot",
)

def setup_unwind_libs(version = None, sha256 = None):
    """Create @unwind_libs for module extensions and direct callers."""
    if "unwind_libs" not in native.existing_rules():
        unwind_libs(
            name = "unwind_libs",
            version = version or VERSIONS["bins_release"],
            sha256 = sha256 or VERSIONS["unwind_libs_sha256"],
        )
