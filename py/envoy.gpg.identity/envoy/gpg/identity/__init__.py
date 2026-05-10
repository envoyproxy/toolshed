
import warnings

from .identity import (
    GPGError,
    GPGIdentity)

DEPRECATION_MESSAGE = (
    "envoy.gpg.identity is deprecated and will no longer be published as a "
    "standalone distribution. Its functionality now ships as part of "
    "envoy.gpg.sign; depend on that instead.")

warnings.warn(
    DEPRECATION_MESSAGE,
    DeprecationWarning,
    stacklevel=2)


__all__ = (
    "GPGError",
    "GPGIdentity")
