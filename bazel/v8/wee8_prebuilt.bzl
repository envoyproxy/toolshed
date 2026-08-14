"""Repository rules for prebuilt V8 wee8 bundles."""

load("//:versions.bzl", "V8_VERSION", "VERSIONS")

WEE8_DEFAULT_STDLIB = "libcxx"
WEE8_STDLIBS = [
    WEE8_DEFAULT_STDLIB,
    "libstdcxx",
]

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

cc_library(
    name = "wee8",
    srcs = ["lib/libwee8.a"],
    hdrs = [":headers"],
    includes = [
        ".",
        "include",
    ],
    linkstatic = True,
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

    ctx.file("BUILD.bazel", _WEE8_BUILD)

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
