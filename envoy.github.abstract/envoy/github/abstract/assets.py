import pathlib
from abc import abstractmethod
from functools import cached_property
from typing import (
    Any, AsyncGenerator, Awaitable, Coroutine, Dict, Iterator,
    Optional, Pattern, Union)

import aiohttp

import abstracts

from aio.functional import async_property

from envoy.github import abstract


class AGithubReleaseAssets(metaclass=abstracts.Abstraction):
    """Base class for Github release assets pusher/fetcher"""

    @abstractmethod
    def __init__(
            self,
            release: "abstract.manager.AGithubRelease",
            path: pathlib.Path) -> None:
        raise NotImplementedError

    @abstractmethod
    async def __aiter__(self) -> AsyncGenerator[
            Dict[str, Union[str, pathlib.Path]], Awaitable]:
        if False:
            yield
        raise NotImplementedError

    @abstractmethod
    def __enter__(self) -> "AGithubReleaseAssets":
        raise NotImplementedError

    @async_property
    @abstractmethod
    async def assets(self) -> Dict:
        """Github release asset dictionaries"""
        raise NotImplementedError

    @async_property
    @abstractmethod
    async def awaitables(
            self) -> AsyncGenerator[
                Coroutine[
                    Any, Any, Dict[str, Union[str, pathlib.Path]]], Dict]:
        raise NotImplementedError


class AGithubReleaseAssetsFetcher(
        AGithubReleaseAssets, metaclass=abstracts.Abstraction):
    """Fetcher of Github release assets"""

    @abstractmethod
    def __init__(
            self,
            release: "abstract.manager.AGithubRelease",
            path: pathlib.Path,
            asset_types: Optional[Dict[str, Pattern[str]]] = None,
            append: Optional[bool] = False) -> None:
        raise NotImplementedError

    @cached_property
    @abstractmethod
    def asset_types(self) -> Dict[str, Pattern[str]]:
        """Patterns for grouping assets"""
        raise NotImplementedError

    @abstractmethod
    def asset_type(self, asset: Dict) -> Optional[str]:
        """Categorization of an asset into an asset type

        The default `asset_types` matcher will just match all files.

        A dictionary of `re` matchers can be provided, eg:

        ```
        asset_types = dict(
            deb=re.compile(".*(\\.deb|\\.changes)$"),
            rpm=re.compile(".*\\.rpm$"))
        ```
        """
        raise NotImplementedError

    @abstractmethod
    async def download(
            self,
            asset: Dict) -> Dict[str, Union[str, pathlib.Path]]:
        """Download an asset"""
        raise NotImplementedError

    @abstractmethod
    async def save(
            self,
            asset_type: str,
            name: str,
            download: aiohttp.ClientResponse) -> Dict[
                str, Union[str, pathlib.Path]]:
        """Save an asset of given type to disk"""
        raise NotImplementedError


class AGithubReleaseAssetsPusher(
        AGithubReleaseAssets, metaclass=abstracts.Abstraction):
    """Pusher of Github release assets"""

    @abstractmethod
    def artefacts(self) -> Iterator[pathlib.Path]:
        """Iterator of matching (ie release file type) artefacts found in a given
        path
        """
        raise NotImplementedError

    @abstractmethod
    async def upload(
            self,
            artefact: pathlib.Path,
            url: str) -> Dict[str, Union[str, pathlib.Path]]:
        """Upload an artefact from a filepath to a given URL"""
        raise NotImplementedError
