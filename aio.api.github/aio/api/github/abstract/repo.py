
import pathlib
from datetime import datetime
from functools import cached_property, partial
from typing import Any, Dict, Optional, Type

import abstracts

from aio.api.github import abstract, utils
from . import base


class AGithubRepo(metaclass=abstracts.Abstraction):
    """A Github repo."""

    def __init__(self, github: "abstract.AGithubAPI", name: str) -> None:
        self.github = github
        self.name = name

    @cached_property
    def github_path(self) -> pathlib.PurePosixPath:
        """Github API repos path."""
        return pathlib.PurePosixPath(f"/repos/{self.name}")

    @cached_property
    def issues(self) -> "abstract.AGithubIssues":
        """Github issues for this repo."""
        return self.github.issues_class(
            self.github,
            repo=self)

    @property
    def labels(self) -> "abstract.AGithubIterator":
        """Github labels for this repo."""
        return self.iter_entities(
            self.github.label_class, "labels")

    async def commit(self, name: str) -> "abstract.AGithubCommit":
        """Fetch a commit for this repo."""
        return self.github.commit_class(
            self,
            await self.getitem(f"commits/{name}"))

    def commits(self, since: datetime = None) -> "abstract.AGithubIterator":
        """Iterate commits for this repo."""
        query = "commits"
        if since is not None:
            query = f"{query}?since={utils.dt_to_js_isoformat(since)}"
        return self.getiter(
            query,
            inflate=partial(self.github.commit_class, self))

    async def getitem(self, query: str) -> Any:
        """Call the `gidgethub.getitem` api for this repo."""
        return await self.github.getitem(self.github_endpoint(query))

    def getiter(self, query: str, **kwargs) -> "abstract.AGithubIterator":
        """Return a `GithubIterator` wrapping `gidgethub.getiter` for this
        repo."""
        return self.github.getiter(self.github_endpoint(query), **kwargs)

    def github_endpoint(self, rel_path: str) -> str:
        """Github API path for provided relative path."""
        return str(self.github_path.joinpath(rel_path))

    def iter_entities(
            self,
            entity: Type[base.GithubEntity],
            path: str,
            **kwargs) -> "abstract.AGithubIterator":
        """Iterate and inflate entities for provided type."""
        return self.getiter(
            path,
            inflate=partial(entity, self),
            **kwargs)

    async def newer_release(
            self,
            since: Optional[datetime] = None) -> Optional[
                "abstract.AGithubRelease"]:
        """Release with the highest semantic version, optionally `since` a
        previous release date.

        Not necessarily the most recent.
        """
        latest_release = None

        async for release in self.releases():
            if since and release.published_at < since:
                break
            is_higher = (
                not release.prerelease
                and release.version
                and (not latest_release
                     or release.version >= latest_release.version))
            if is_higher:
                latest_release = release
        return latest_release

    async def patch(self, query: str, data: Optional[Dict] = None) -> Any:
        """Call the `gidgethub.patch` api for this repo."""
        return await self.github.patch(self.github_endpoint(query), data=data)

    async def post(self, query: str, data: Optional[Dict] = None) -> Any:
        """Call the `gidgethub.post` api for this repo."""
        return await self.github.post(self.github_endpoint(query), data=data)

    async def release(self, name: str) -> "abstract.AGithubRelease":
        """Fetch a release for this repo."""
        return self.github.release_class(
            self,
            await self.getitem(f"releases/tags/{name}"))

    def releases(self) -> "abstract.AGithubIterator":
        """Iterate releases for this repo."""
        return self.iter_entities(
            self.github.release_class,
            "releases?per_page=100")

    async def tag(self, name: str) -> "abstract.AGithubTag":
        """Fetch a tag for this repo."""
        # TODO: these dont always give back the same kinda objects
        #   check what pygithub does.
        ref_tag = await self.getitem(f"git/ref/tags/{name}")
        tag = await self.github.getitem(ref_tag["object"]["url"])
        # print(ref_tag["object"]["url"])
        return self.github.tag_class(self, tag)

    def tags(self) -> "abstract.AGithubIterator":
        """Iterate tags for this repo."""
        return self.iter_entities(
            self.github.tag_class,
            "tags")
