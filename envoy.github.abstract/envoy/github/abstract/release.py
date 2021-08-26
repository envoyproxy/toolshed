import pathlib
from abc import abstractmethod
from typing import (
    Dict, Iterable, List,
    Optional, Pattern, Set, Type, Union)

import aiohttp

import gidgethub.abc

import abstracts

from aio.functional import async_property

from .assets import (
    AGithubReleaseAssetsFetcher, AGithubReleaseAssetsPusher)
from envoy.github import abstract


class AGithubRelease(metaclass=abstracts.Abstraction):
    """A Github tagged release version

    Provides CRUD operations for a release and its assets, and therefore
    can exist already, or be created.
    """

    @abstractmethod
    def __init__(
            self,
            manager: "abstract.manager.AGithubReleaseManager",
            version: str):
        raise NotImplementedError

    @async_property(cache=True)
    @abstractmethod
    async def asset_names(self) -> Set[str]:
        """Set of the names of assets for this release version"""
        raise NotImplementedError

    @async_property(cache=True)
    @abstractmethod
    async def assets(self) -> Dict:
        raise NotImplementedError

    @property
    @abstractmethod
    def fetcher(self) -> Type[AGithubReleaseAssetsFetcher]:
        """An instance of `AGithubReleaseAssetsFetcher` for fetching release
        assets.
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def github(self) -> gidgethub.abc.GitHubAPI:
        raise NotImplementedError

    @property
    @abstractmethod
    def pusher(self) -> Type[AGithubReleaseAssetsPusher]:
        """An instance of `AGithubReleaseAssetsPusher` for pushing release
        assets.
        """
        raise NotImplementedError

    @async_property(cache=True)
    @abstractmethod
    async def release(self) -> Dict:
        raise NotImplementedError

    @property
    @abstractmethod
    def session(self) -> aiohttp.ClientSession:
        raise NotImplementedError

    @property
    @abstractmethod
    def version(self) -> str:
        raise NotImplementedError

    @abstractmethod
    async def create(
        self,
        assets: Optional[List[pathlib.Path]] = None
    ) -> Dict[str, Union[List[Dict[str, Union[str, pathlib.Path]]], Dict]]:
        """Create this release version and optionally upload provided assets"""
        raise NotImplementedError

    @abstractmethod
    async def delete(self) -> None:
        """Delete this release version"""
        raise NotImplementedError

    @abstractmethod
    def fail(self, message: str) -> str:
        raise NotImplementedError

    @abstractmethod
    async def fetch(
            self,
            path: pathlib.Path,
            asset_types: Optional[Dict[str, Pattern[str]]] = None,
            append: Optional[bool] = False) -> Dict[
                str,
                List[Dict[str, Union[str, pathlib.Path]]]]:
        """Fetch assets for this version, saving either to a directory or
        tarball
        """
        raise NotImplementedError

    @abstractmethod
    async def get(self) -> Dict:
        """Get the release information for this Github release."""
        raise NotImplementedError

    @abstractmethod
    async def push(
            self, artefacts: Iterable[pathlib.Path]
    ) -> Dict[str, List[Dict[str, Union[str, pathlib.Path]]]]:
        """Push assets from a list of paths, either directories or tarballs."""
        raise NotImplementedError

    @async_property(cache=True)
    @abstractmethod
    async def upload_url(self) -> str:
        """Upload URL for this release version"""
        raise NotImplementedError
