"""Repository rules for prebuilt V8 wee8 bundles."""

load("//:versions.bzl", "V8_VERSION", "VERSIONS")

WEE8_DEFAULT_STDLIB = "libcxx"
WEE8_STDLIBS = [
    WEE8_DEFAULT_STDLIB,
    "libstdcxx",
]

# V8 build-time defines that the source @v8//:wee8 target propagates to its
# consumers (captured via `bazel aquery` on a V8 CppCompile action). These are
# ABI-affecting and/or gate public V8 headers (e.g. V8_ENABLE_WEBASSEMBLY guards
# src/wasm/c-api.h), so the prebuilt must re-expose them or consumers compiling
# against libwee8.a (e.g. proxy_wasm_cpp_host's v8.cc) get header errors / ABI
# skew. Arch-specific target define is appended per-repo (see _WEE8_ARCH_DEFINE).
_WEE8_COMMON_DEFINES = [
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
    "V8_TARGET_OS_LINUX",
    "V8_TLS_USED_IN_LIBRARY",
    "V8_TYPED_ARRAY_MAX_SIZE_IN_HEAP=64",
]

_WEE8_ARCH_DEFINE = {
    "x86_64": "V8_TARGET_ARCH_X64",
    "aarch64": "V8_TARGET_ARCH_ARM64",
}

_WEE8_BUILD = """\
package(default_visibility = ["//visibility:public"])

filegroup(
    name = "headers",
    srcs = glob(
        [
            "include/**",
            "third_party/**/*.h",
            "third_party/**/*.hh",
            "src/**/*.h",
        ],
    ),
)

filegroup(
    name = "libs",
    srcs = ["lib/libwee8.a"],
)

# The wasm C-API public headers are #included as "wasm-api/wasm.hh", mirroring
# the source @v8//:wee8 target's strip_include_prefix = "third_party" (scoped so
# it does not put the rest of third_party/ on the include path).
cc_library(
    name = "wasm_c_api_headers",
    hdrs = glob(
        [
            "third_party/wasm-api/*.h",
            "third_party/wasm-api/*.hh",
        ],
    ),
    strip_include_prefix = "third_party",
)

cc_library(
    name = "wee8",
    srcs = ["lib/libwee8.a"],
    hdrs = [":headers"],
    includes = [
        ".",
        "include",
    ],
    defines = [
{defines}
    ],
    linkstatic = True,
    # abseil/icu are deliberately excluded from libwee8.a (consumers provide
    # their own). Re-expose abseil's compile context (v8.cc #includes absl
    # headers directly) and the wasm C-API headers so the prebuilt is a drop-in
    # for the source @v8//:wee8.
    deps = [
        ":wasm_c_api_headers",
        "@abseil-cpp//absl/strings:str_format",
    ],
)
"""

_MISSING_WEE8_BUILD = """\
package(default_visibility = ["//visibility:public"])

filegroup(
    name = "headers",
    srcs = [],
)

filegroup(
    name = "libs",
    srcs = [],
)

cc_library(
    name = "wee8",
    hdrs = [],
    srcs = [],
    deprecation = "{message}",
    target_compatible_with = ["@platforms//:incompatible"],
)
"""

def wee8_archive_filename(version, arch, stdlib = WEE8_DEFAULT_STDLIB):
    if stdlib == WEE8_DEFAULT_STDLIB:
        return wee8_legacy_archive_filename(version, arch)
    return "v8-wee8-%s-linux-%s-%s.tar.xz" % (version, arch, stdlib)

def wee8_legacy_archive_filename(version, arch):
    return "v8-wee8-%s-linux-%s.tar.xz" % (version, arch)

def wee8_prebuilt_repo_name(arch, stdlib = WEE8_DEFAULT_STDLIB):
    if stdlib == WEE8_DEFAULT_STDLIB:
        return "wee8_prebuilt_%s" % arch
    return "wee8_prebuilt_%s_libstdcxx" % arch

def wee8_sha256(versions, arch, stdlib = WEE8_DEFAULT_STDLIB):
    arch_entry = versions.get("wee8_sha256", {}).get(arch, "")
    if type(arch_entry) == "dict":
        return arch_entry.get(stdlib, "")
    if stdlib == WEE8_DEFAULT_STDLIB:
        return arch_entry
    return ""

def _resolve_wee8_sha256(arch, stdlib, sha256 = None):
    resolved = sha256 or wee8_sha256(VERSIONS, arch, stdlib)
    if resolved:
        return resolved
    fail(
        "Missing sha256 for published wee8 variant linux-%s (%s) in //:versions.bzl" % (
            arch,
            stdlib,
        ),
    )

def _missing_wee8_message(version, arch, stdlib):
    return (
        "Missing wee8 prebuilt archive for linux-%s (%s). " +
        "Expected release artifact %s in bins-v%s and update //:versions.bzl " +
        "with the matching wee8_sha256 entry."
    ) % (
        arch,
        stdlib,
        wee8_archive_filename(V8_VERSION, arch, stdlib),
        version,
    )

def _wee8_prebuilt_impl(ctx):
    """Implementation for wee8 prebuilt repository rule."""
    sha256 = ctx.attr.sha256
    if sha256:
        ctx.download_and_extract(
            url = "https://github.com/envoyproxy/toolshed/releases/download/bins-v{version}/{archive}".format(
                version = ctx.attr.version,
                archive = wee8_archive_filename(V8_VERSION, ctx.attr.arch, ctx.attr.stdlib),
            ),
            sha256 = sha256,
        )
    else:
        ctx.file(
            "BUILD.bazel",
            _MISSING_WEE8_BUILD.format(
                message = _missing_wee8_message(
                    ctx.attr.version,
                    ctx.attr.arch,
                    ctx.attr.stdlib,
                ),
            ),
        )
        return

    defines = list(_WEE8_COMMON_DEFINES)
    arch_define = _WEE8_ARCH_DEFINE.get(ctx.attr.arch)
    if arch_define:
        defines.append(arch_define)
    defines_block = "\n".join(['        "%s",' % define for define in defines])
    ctx.file("BUILD.bazel", _WEE8_BUILD.format(defines = defines_block))

_ARCHES = ["x86_64", "aarch64"]

wee8_prebuilt = repository_rule(
    implementation = _wee8_prebuilt_impl,
    attrs = {
        "version": attr.string(
            mandatory = True,
            doc = "Release version to download",
        ),
        "sha256": attr.string(
            mandatory = True,
            doc = "SHA256 hash of the wee8 archive.",
        ),
        "arch": attr.string(
            mandatory = True,
            values = ["x86_64", "aarch64"],
            doc = "Architecture to target",
        ),
        "stdlib": attr.string(
            default = WEE8_DEFAULT_STDLIB,
            values = WEE8_STDLIBS,
            doc = "C++ standard library ABI variant to target",
        ),
    },
    doc = "Downloads prebuilt wee8 bundles for cross-compilation",
)

def setup_wee8_prebuilt(
        x86_64_version = None,
        x86_64_sha256 = None,
        x86_64_libstdcxx_version = None,
        x86_64_libstdcxx_sha256 = None,
        aarch64_version = None,
        aarch64_sha256 = None):
    """Setup function for WORKSPACE and bzlmod."""
    variants = [
        ("x86_64", WEE8_DEFAULT_STDLIB, x86_64_version, x86_64_sha256),
        ("x86_64", "libstdcxx", x86_64_libstdcxx_version or x86_64_version, x86_64_libstdcxx_sha256),
        ("aarch64", WEE8_DEFAULT_STDLIB, aarch64_version, aarch64_sha256),
    ]
    for arch, stdlib, version, sha256 in variants:
        wee8_prebuilt(
            name = wee8_prebuilt_repo_name(arch, stdlib),
            version = version or VERSIONS["bins_release"],
            sha256 = _resolve_wee8_sha256(arch, stdlib, sha256),
            arch = arch,
            stdlib = stdlib,
        )
