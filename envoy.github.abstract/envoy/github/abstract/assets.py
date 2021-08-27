import pathlib
import re
import tempfile
from abc import abstractmethod
from functools import cached_property
from typing import (
    Any, AsyncGenerator, Awaitable, Coroutine, Dict, Iterator,
    Optional, Pattern, Set, Union)

import aiohttp

import gidgethub.abc

import abstracts

from aio.functional import async_property
from aio.tasks import concurrent, ConcurrentError, ConcurrentIteratorError

from envoy.github import abstract

from .exceptions import GithubReleaseError


AssetsResultDict = Dict[str, Union[str, pathlib.Path]]
AssetsAwaitableGenerator = AsyncGenerator[
    Coroutine[
        Any,
        Any,
        AssetsResultDict],
    Dict]
AssetsGenerator = AsyncGenerator[
    AssetsResultDict,
    Awaitable]
AssetTypesDict = Dict[str, Pattern[str]]


class AGithubReleaseAssets(metaclass=abstracts.Abstraction):
    """Base class for Github release assets pusher/fetcher"""
    _concurrency = 4

    def __init__(
            self,
            release: "abstract.manager.AGithubRelease",
            path: pathlib.Path) -> None:
        self._release = release
        self._path = path

    async def __aiter__(self) -> AssetsGenerator:
        with self:
            try:
                async for result in self.run():
                    yield result
            except ConcurrentIteratorError as e:
                raise GithubReleaseError(e.args[0])

    def __enter__(self) -> "AGithubReleaseAssets":
        return self

    def __exit__(self, *args) -> None:
        self.cleanup()

    @async_property
    async def assets(self) -> Dict:
        """Github release asset dictionaries"""
        return await self.release.assets

    @async_property
    @abstracts.interfacemethod
    async def awaitables(self) -> AssetsAwaitableGenerator:
        if False:
            yield
        raise NotImplementedError

    @property
    @abstractmethod
    def concurrency(self) -> int:
        return self._concurrency

    @property
    def github(self) -> gidgethub.abc.GitHubAPI:
        return self.release.github

    @property
    @abstractmethod
    def path(self) -> pathlib.Path:
        return self._path

    @property
    def release(self) -> "abstract.manager.AGithubRelease":
        return self._release

    @property
    def session(self) -> aiohttp.ClientSession:
        return self.release.session

    @property
    def tasks(self) -> concurrent:
        return concurrent(self.awaitables, limit=self.concurrency)

    @cached_property
    def tempdir(self) -> tempfile.TemporaryDirectory:
        return tempfile.TemporaryDirectory()

    @property
    def version(self) -> str:
        return self.release.version

    def cleanup(self) -> None:
        if "tempdir" in self.__dict__:
            self.tempdir.cleanup()
            del self.__dict__["tempdir"]

    def fail(self, message: str) -> str:
        return self.release.fail(message)

    async def handle_result(self, result: Any) -> Any:
        return result

    async def run(self) -> AssetsGenerator:
        try:
            async for result in self.tasks:
                yield result
        except ConcurrentIteratorError as e:
            # This should catch any errors running the upload coros
            # In this case the exception is unwrapped, and the original
            # error is raised.
            raise e.args[0]
        except ConcurrentError as e:
            yield dict(error=self.fail(e.args[0]))


class AGithubReleaseAssetsFetcher(
        AGithubReleaseAssets, metaclass=abstracts.Abstraction):
    """Fetcher of Github release assets"""

    def __init__(
            self,
            release: "abstract.manager.AGithubRelease",
            path: pathlib.Path,
            asset_types: Optional[AssetTypesDict] = None,
            append: Optional[bool] = False) -> None:
        super().__init__(release, path)
        self._asset_types = asset_types
        self._append = append

    @property
    def append(self) -> bool:
        """Append to existing file or otherwise"""
        return self._append or False

    @cached_property
    def asset_types(self) -> Dict[str, Pattern[str]]:
        """Patterns for grouping assets"""
        return self._asset_types or dict(assets=re.compile(".*"))

    @async_property
    async def awaitables(self) -> AssetsAwaitableGenerator:
        # assets categorised according to asset_types
        for asset in await self.assets:
            asset_type = self.asset_type(asset)
            if not asset_type:
                continue
            asset["asset_type"] = asset_type
            yield self.download(asset)

    @property
    def write_mode(self) -> str:
        return "a" if self.append else "w"

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
        for k, v in self.asset_types.items():
            if v.search(asset["name"]):
                return k

    @abstracts.interfacemethod
    async def download(
            self,
            asset: Dict) -> AssetsResultDict:
        """Download an asset"""
        raise NotImplementedError

    @abstracts.interfacemethod
    async def save(
            self,
            asset_type: str,
            name: str,
            download: aiohttp.ClientResponse) -> AssetsResultDict:
        """Save an asset of given type to disk"""
        raise NotImplementedError


class AGithubReleaseAssetsPusher(
        AGithubReleaseAssets, metaclass=abstracts.Abstraction):
    """Pusher of Github release assets"""

    @property  # type:ignore
    @abstracts.interfacemethod
    def artefacts(self) -> Iterator[pathlib.Path]:
        """Iterator of matching (ie release file type) artefacts found in a given
        path
        """
        raise NotImplementedError

    @async_property
    async def asset_names(self) -> Set[str]:
        return await self.release.asset_names

    @async_property
    async def awaitables(self) -> AssetsAwaitableGenerator:
        for artefact in self.artefacts:
            yield self.upload(
                artefact,
                await self.artefact_url(artefact.name))

    @async_property
    async def upload_url(self) -> str:
        return await self.release.upload_url

    async def artefact_url(self, name: str) -> str:
        """URL to upload a provided artefact name as an asset"""
        return f"{await self.upload_url}?name={name}"

    @abstracts.interfacemethod
    async def upload(
            self,
            artefact: pathlib.Path,
            url: str) -> AssetsResultDict:
        """Upload an artefact from a filepath to a given URL"""
        raise NotImplementedError
