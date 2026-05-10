
import warnings

from .distrotest import (
    BuildError,
    ConfigurationError,
    ContainerError,
    DistroTestConfig,
    DistroTestImage,
    DistroTest)


DEPRECATION_MESSAGE = (
    "envoy.distribution.distrotest is deprecated and will no longer be "
    "published as a standalone distribution. Its functionality now ships as "
    "part of envoy.distribution.verify; depend on that instead.")

warnings.warn(
    DEPRECATION_MESSAGE,
    DeprecationWarning,
    stacklevel=2)


__all__ = (
    "BuildError",
    "ConfigurationError",
    "ContainerError",
    "DistroTestConfig",
    "DistroTestImage",
    "DistroTest")
