"""Load check for //pgp:extensions.bzl.

The extension is not used by this repo (no `sq` platform is enabled by
default), so this ensures it is at least loaded and evaluated in CI.
"""

load("//pgp:extensions.bzl", "SQ_PLATFORMS", "pgp_extension", "sq_repository")

SQ_PLATFORM_NAMES = sorted(SQ_PLATFORMS)

_LOADED = [pgp_extension, sq_repository]
