
import warnings

from .assets import (
    AGithubReleaseAssets,
    AGithubReleaseAssetsPusher,
    AGithubReleaseAssetsFetcher,
    AssetsAwaitableGenerator,
    AssetsGenerator,
    AssetsResultDict,
    AssetTypesDict)

from .command import AGithubReleaseCommand
from .exceptions import GithubReleaseError
from .manager import AGithubReleaseManager
from .release import AGithubRelease, ReleaseDict
from .runner import AGithubReleaseRunner

DEPRECATION_MESSAGE = (
    "envoy.github.abstract is deprecated and will no longer be published as a "
    "standalone distribution. Its functionality now ships as part of "
    "envoy.github.release; depend on that instead.")

warnings.warn(
    DEPRECATION_MESSAGE,
    DeprecationWarning,
    stacklevel=2)


__all__ = (
    "AGithubRelease",
    "AGithubReleaseAssets",
    "AGithubReleaseAssetsPusher",
    "AGithubReleaseAssetsFetcher",
    "AGithubReleaseCommand",
    "AGithubReleaseManager",
    "AGithubReleaseRunner",
    "AssetsAwaitableGenerator",
    "AssetsGenerator",
    "AssetsResultDict",
    "AssetTypesDict",
    "GithubReleaseError",
    "ReleaseDict")
