
import asyncio
import hashlib
import logging
import time
from concurrent import futures
from datetime import datetime
from functools import cached_property

from packaging import version

import aiohttp

import gidgethub

import abstracts

from aio.api import github as _github
from aio.core import event
from aio.core.functional import async_property

from envoy.base import utils
from envoy.dependency.check import exceptions


logger = logging.getLogger(__name__)

MIN_DATA_SIZE_TO_HASH_IN_PROC = 1000000


@abstracts.implementer(event.IExecutive)
class ADependencyGithubRelease(
        event.AExecutive,
        metaclass=abstracts.Abstraction):
    """Github release associated with a dependency."""

    @classmethod
    def hash_file_data(cls, data: bytes) -> str:
        file_hash = hashlib.sha256()
        file_hash.update(data)
        return str(file_hash.hexdigest())

    def __init__(
            self,
            repo: _github.IGithubRepo,
            version: str,
            asset_url: str | None = None,
            release: _github.IGithubRelease | None = None,
            loop: asyncio.AbstractEventLoop | None = None,
            pool: futures.Executor | None = None) -> None:
        self.repo = repo
        self.asset_url = asset_url
        self._version = version
        self._release = release
        self._pool = pool
        self._loop = loop

    @async_property(cache=True)
    async def commit(self) -> _github.IGithubCommit | None:
        """Github commit for this release."""
        try:
            return await self.repo.commit(self.tag_name)  # type:ignore
        except gidgethub.BadRequest as e:
            if e.args[0] == "Not Found":
                return None
            raise e

    @async_property(cache=True)
    async def date(self) -> str | None:
        """UTC date of this release."""
        # TODO(phlax): add tests for this and related fun
        return (
            utils.dt_to_utc_isoformat(timestamp)
            if (timestamp := await self.timestamp)
            else None)

    @property
    def github(self) -> _github.IGithubAPI:
        return self.repo.github

    @property
    def min_data_size_to_hash_in_proc(self) -> int:
        return MIN_DATA_SIZE_TO_HASH_IN_PROC

    @async_property(cache=True)
    async def release(self) -> _github.IGithubRelease | None:
        """Github release."""
        if self._release:
            return self._release
        try:
            return await self.repo.release(self.tag_name)  # type:ignore
        except gidgethub.BadRequest as e:
            if e.args[0] == "Not Found":
                return None
            raise e

    @property
    def session(self) -> aiohttp.ClientSession:
        return self.github.session

    @async_property(cache=True)
    async def sha(self) -> str:
        """Release SHA."""
        if not self.asset_url:
            raise exceptions.NoReleaseAssetError(
                f"Cannot check sha for {self.__class__.__name__} "
                "with no `asset_url`")
        async with self.session.get(self.asset_url) as response:
            response.raise_for_status()
            logger.debug("SHA download: %s", self.asset_url)
            return await self._hash_file_data(await response.read())

    @async_property(cache=True)
    async def tag(self) -> _github.IGithubTag | None:
        """Github tag."""
        try:
            return await self.repo.tag(self.tag_name)  # type:ignore
        except (gidgethub.BadRequest, _github.exceptions.TagNotFound) as e:
            do_raise = (
                isinstance(e, gidgethub.BadRequest)
                and e.args[0] != "Not Found")
            if do_raise:
                raise e
            return None

    @property
    def tag_name(self) -> str:
        """Github tag name."""
        return self._version

    @cached_property
    def tagged(self) -> bool:
        """Flag to indicate whether this release has a name."""
        return not utils.is_sha(self.tag_name)

    @async_property(cache=True)
    async def timestamp(self) -> datetime | None:
        """Timestamp of this release."""
        return (
            await self.timestamp_tag
            if self.tagged
            else await self.timestamp_commit)

    @async_property(cache=True)
    async def timestamp_commit(self) -> datetime | None:
        """Timestamp of the commit of this release."""
        return (
            commit.timestamp
            if (commit := await self.commit)
            else None)

    @async_property(cache=True)
    async def timestamp_tag(self) -> datetime | None:
        """Timestamp of this release, resolved from the release, tag, or
        commit, in that order."""
        if release := await self.release:
            return release.published_at
        if await self.tag:
            return (await (await self.tag).commit).timestamp
        # Its not clear why this is required - it seems to be legacy tags
        # in this case fetching the `tag_name` as a commit seems to work.
        return await self.timestamp_commit

    @cached_property
    def version(self) -> version.Version | None:
        """Semantic version of this release."""
        try:
            return version.parse(self.tag_name)
        except version.InvalidVersion:
            return None

    def should_hash_in_proc(self, data: bytes) -> bool:
        """Conditionally generate SHA hashes based on incoming data."""
        return len(data) > self.min_data_size_to_hash_in_proc

    async def _hash_file_data(self, data: bytes) -> str:
        hash_in_proc = self.should_hash_in_proc(data)
        start = time.perf_counter()
        sha = (
            await self.execute(self.hash_file_data, data)
            if hash_in_proc
            else self.hash_file_data(data))
        logger.debug(
            "SHA parsed in {:.3f}s{}: {}" .format(
                time.perf_counter() - start,
                (" (fork: True)"
                 if hash_in_proc
                 else ""),
                self.asset_url))
        return sha
