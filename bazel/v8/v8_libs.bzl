"""Repository rule for pre-built V8 (wee8) static library."""

_ARCH_MAP = {
    "amd64": "x86_64",
    "x86_64": "x86_64",
    "aarch64": "aarch64",
    "arm64": "aarch64",
}

_BUILD_FILE_CONTENT = """
package(default_visibility = ["//visibility:public"])

cc_import(
    name = "wee8_import",
    static_library = "lib/libwee8.a",
    alwayslink = True,
)

cc_library(
    name = "wee8",
    hdrs = glob(["include/**/*.h", "include/**/*.hh", "src/**/*.h", "third_party/**/*.h", "third_party/**/*.hh"]),
    defines = [
        "GOOGLE3",
        "V8_ADVANCED_BIGINT_ALGORITHMS",
        "V8_CONCURRENT_MARKING",
        "V8_DEPRECATION_WARNINGS",
        "V8_ENABLE_CONTINUATION_PRESERVED_EMBEDDER_DATA",
        "V8_ENABLE_EXTENSIBLE_RO_SNAPSHOT",
        "V8_ENABLE_LAZY_SOURCE_POSITIONS",
        "V8_ENABLE_MAGLEV",
        "V8_ENABLE_SPARKPLUG",
        "V8_ENABLE_TURBOFAN",
        "V8_ENABLE_UNDEFINED_DOUBLE",
        "V8_ENABLE_WEBASSEMBLY",
        "V8_HAVE_TARGET_OS",
        "V8_IMMINENT_DEPRECATION_WARNINGS",
        "V8_TARGET_ARCH_X64",
        "V8_TARGET_OS_LINUX",
        "V8_TLS_USED_IN_LIBRARY",
        "V8_TYPED_ARRAY_MAX_SIZE_IN_HEAP=64",
    ],
    includes = [".", "include", "third_party"],
    deps = [
        ":wee8_import",
        "@abseil-cpp//absl/container:btree",
        "@abseil-cpp//absl/container:flat_hash_map",
        "@abseil-cpp//absl/container:flat_hash_set",
        "@abseil-cpp//absl/functional:overload",
        "@abseil-cpp//absl/synchronization",
        "@abseil-cpp//absl/time",
    ],
    visibility = ["//visibility:public"],
)
"""

def _v8_prebuilt_impl(ctx):
    """Downloads pre-built V8 wee8 library from GitHub releases."""

    # Auto-detect host architecture
    host_arch = ctx.os.arch
    arch = _ARCH_MAP.get(host_arch)
    if not arch:
        fail("Unsupported host architecture for V8 pre-built: %s" % host_arch)

    # Allow local testing via V8_PREBUILT_PATH environment variable.
    # When set, it should point to a directory containing the tarball, e.g.:
    #   export V8_PREBUILT_PATH=/tmp/v8-prebuilt
    local_path = ctx.os.environ.get("V8_PREBUILT_PATH", "")
    if local_path:
        tarball = "{path}/v8-wee8-{version}-linux-{arch}.tar.xz".format(
            path = local_path,
            version = ctx.attr.version,
            arch = arch,
        )
        ctx.extract(ctx.path(tarball))
    else:
        sha256 = ctx.attr.sha256.get(arch, "")
        if not sha256:
            fail("No V8 pre-built SHA256 provided for architecture: %s" % arch)

        ctx.download_and_extract(
            url = "https://github.com/envoyproxy/toolshed/releases/download/v8-v{version}/v8-wee8-{version}-linux-{arch}.tar.xz".format(
                version = ctx.attr.version,
                arch = arch,
            ),
            sha256 = sha256,
        )
    ctx.file("BUILD.bazel", _BUILD_FILE_CONTENT)

v8_prebuilt = repository_rule(
    implementation = _v8_prebuilt_impl,
    attrs = {
        "version": attr.string(
            mandatory = True,
            doc = "V8 version (e.g., '14.6.202.10')",
        ),
        "sha256": attr.string_dict(
            mandatory = True,
            doc = "SHA256 hashes keyed by architecture (x86_64, aarch64)",
        ),
    },
    environ = ["V8_PREBUILT_PATH"],
    doc = "Downloads pre-built V8 wee8 static library for use with proxy-wasm",
)

def setup_v8_prebuilt(version, sha256):
    """Setup function for WORKSPACE.

    Creates @v8 repository with pre-built wee8 library.
    The host architecture is auto-detected at fetch time.

    Args:
        version: V8 version to download (must be already published).
        sha256: Dict of {arch: sha256} for each supported architecture.
    """
    v8_prebuilt(
        name = "v8",
        version = version,
        sha256 = sha256,
    )
