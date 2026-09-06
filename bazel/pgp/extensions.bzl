"""Module extension fetching the default OpenPGP signer binary (`sq`).

Sequoia PGP's `sq` is a single, statically linkable Rust OpenPGP
implementation with no agent, home directory or keyring state to fight - the
same OpenPGP implementation used as the backend for `rpm` on Fedora/RHEL and
as `sqv` in apt >= 3.0.

Upstream does not publish sha256-verifiable release binaries that could be
pinned here, so **no platform is fetched by default** - each platform must be
enabled by passing a sha256 you have verified yourself:

```starlark
sq = use_extension("@envoy_toolshed//pgp:extensions.bzl", "pgp_extension")
sq.setup(
    version = "1.4.0",
    sha256s = {
        "linux_x86_64": "<sha256 of the binary you verified>",
    },
)
use_repo(sq, "sq_linux_x86_64")
register_toolchains("@sq_linux_x86_64//:toolchain")
```

`urls` can be used to point at your own (audited, mirrored) copy of the
binary.
"""

# TODO(pgp): pin verified sha256s here once upstream publishes signed,
#   reproducible release binaries. The URLs below are the upstream release
#   artifact locations - they are unverified, so the corresponding platforms
#   are disabled until a sha256 is supplied by the consumer.
SQ_VERSION = "1.4.0"

SQ_PLATFORMS = {
    "darwin_aarch64": struct(
        # TODO(pgp): unverified, sha256 required to enable.
        url = "https://gitlab.com/sequoia-pgp/sequoia-sq/-/releases/v{version}/downloads/sq-{version}-aarch64-apple-darwin",
        exec_compatible_with = [
            "@platforms//os:macos",
            "@platforms//cpu:aarch64",
        ],
    ),
    "linux_aarch64": struct(
        # TODO(pgp): unverified, sha256 required to enable.
        url = "https://gitlab.com/sequoia-pgp/sequoia-sq/-/releases/v{version}/downloads/sq-{version}-aarch64-unknown-linux-musl",
        exec_compatible_with = [
            "@platforms//os:linux",
            "@platforms//cpu:aarch64",
        ],
    ),
    "linux_x86_64": struct(
        # TODO(pgp): unverified, sha256 required to enable.
        url = "https://gitlab.com/sequoia-pgp/sequoia-sq/-/releases/v{version}/downloads/sq-{version}-x86_64-unknown-linux-musl",
        exec_compatible_with = [
            "@platforms//os:linux",
            "@platforms//cpu:x86_64",
        ],
    ),
}

_BUILD_FILE = """
load("@envoy_toolshed//pgp:defs.bzl", "pgp_toolchain", "sq_signer")

package(default_visibility = ["//visibility:public"])

exports_files(["sq"])

sq_signer(
    name = "signer",
    sq = "sq",
)

pgp_toolchain(
    name = "signer_toolchain",
    signer = ":signer",
)

toolchain(
    name = "toolchain",
    exec_compatible_with = {exec_compatible_with},
    toolchain = ":signer_toolchain",
    toolchain_type = "@envoy_toolshed//pgp:toolchain_type",
)
"""

def _sq_repository_impl(ctx):
    ctx.download(
        url = ctx.attr.urls,
        sha256 = ctx.attr.sha256,
        output = "sq",
        executable = True,
    )
    ctx.file(
        "BUILD",
        _BUILD_FILE.format(exec_compatible_with = str(ctx.attr.exec_compatible_with)),
        executable = False,
    )

sq_repository = repository_rule(
    implementation = _sq_repository_impl,
    doc = "Downloads a `sq` binary and exposes it as an OpenPGP signer toolchain.",
    attrs = {
        "exec_compatible_with": attr.string_list(
            doc = "Execution platform constraints for the toolchain.",
            mandatory = True,
        ),
        "sha256": attr.string(
            doc = "Verified sha256 of the `sq` binary.",
            mandatory = True,
        ),
        "urls": attr.string_list(
            doc = "URLs to download the `sq` binary from.",
            mandatory = True,
        ),
    },
)

def _sq_repo(platform, version, url, sha256):
    sq_repository(
        name = "sq_%s" % platform,
        urls = [url.format(version = version)],
        sha256 = sha256,
        exec_compatible_with = SQ_PLATFORMS[platform].exec_compatible_with,
    )

def _pgp_extension_impl(module_ctx):
    for mod in module_ctx.modules:
        for tag in mod.tags.setup:
            version = tag.version or SQ_VERSION
            for platform, sha256 in tag.sha256s.items():
                if platform not in SQ_PLATFORMS:
                    fail("Unknown `sq` platform: %s (expected one of %s)" % (
                        platform,
                        sorted(SQ_PLATFORMS),
                    ))
                if not sha256:
                    fail("No sha256 given for `sq` platform: %s" % platform)
                _sq_repo(
                    platform,
                    version,
                    tag.urls.get(platform) or SQ_PLATFORMS[platform].url,
                    sha256,
                )

_setup = tag_class(
    attrs = {
        "sha256s": attr.string_dict(
            doc = "Verified sha256 of the `sq` binary, keyed by platform.",
        ),
        "urls": attr.string_dict(
            doc = "Override download URL, keyed by platform.",
        ),
        "version": attr.string(
            doc = "`sq` version to fetch.",
            default = SQ_VERSION,
        ),
    },
)

pgp_extension = module_extension(
    implementation = _pgp_extension_impl,
    tag_classes = {
        "setup": _setup,
    },
)
