
from datetime import datetime
from functools import cached_property
from typing import Optional, Union

from packaging import version

import gidgethub

import abstracts

from aio.api import github
from aio.functional import async_property

from envoy.base import utils


class ADependencyGithubRelease(metaclass=abstracts.Abstraction):
    """Github release associated with a dependency."""

    def __init__(
            self,
            repo: github.AGithubRepo,
            version: str,
            release: Optional[github.AGithubRelease] = None) -> None:
        self.repo = repo
        self._version = version
        self._release = release

    @async_property(cache=True)
    async def commit(self) -> Optional[github.AGithubCommit]:
        """Github commit for this release."""
        try:
            return await self.repo.commit(self.tag_name)
        except gidgethub.BadRequest as e:
            if e.args[0] == "Not Found":
                return None
            raise e

    @async_property(cache=True)
    async def date(self) -> str:
        """UTC date of this release."""
        return utils.dt_to_utc_isoformat(await self.timestamp)

    @async_property(cache=True)
    async def release(self) -> Optional[github.AGithubRelease]:
        """Github release."""
        if self._release:
            return self._release
        try:
            return await self.repo.release(self.tag_name)
        except gidgethub.BadRequest as e:
            if e.args[0] == "Not Found":
                return None
            raise e

    @async_property(cache=True)
    async def tag(self) -> Optional[github.AGithubTag]:
        """Github tag."""
        try:
            return await self.repo.tag(self.tag_name)
        except (gidgethub.BadRequest, github.exceptions.TagNotFound) as e:
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
    async def timestamp(self) -> datetime:
        """Timestamp of this release."""
        return (
            await self.timestamp_tag
            if self.tagged
            else await self.timestamp_commit)

    @async_property(cache=True)
    async def timestamp_commit(self) -> datetime:
        """Timestamp of the commit of this release."""
        return (await self.commit).timestamp

    @async_property(cache=True)
    async def timestamp_tag(self) -> datetime:
        """Timestamp of this release, resolved from the release, tag, or
        commit, in that order."""
        if await self.release:
            return (await self.release).published_at
        if await self.tag:
            return (await (await self.tag).commit).timestamp
        # Its not clear why this is required - it seems to be legacy tags
        # in this case fetching the `tag_name` as a commit seems to work.
        return await self.timestamp_commit

    @cached_property
    def version(
            self) -> Union[
                version.LegacyVersion,
                version.Version]:
        """Semantic version of this release."""
        return version.parse(self.tag_name)
