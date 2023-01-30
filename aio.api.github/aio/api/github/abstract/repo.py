
import pathlib
from datetime import datetime
from functools import cached_property, partial
from typing import Any, Dict, Optional, Type

import gidgethub

import abstracts

from aio.api.github import exceptions, interface, utils
from . import base


class AGithubRepo(metaclass=abstracts.Abstraction):
    """A Github repo."""

    def __init__(self, github: "interface.IGithubAPI", name: str) -> None:
        self._github = github
        self._name = name

    def __str__(self):
        return f"<{self.__class__.__name__} {self.name}>"

    @cached_property
    def github_path(self) -> pathlib.PurePosixPath:
        """Github API repos path."""
        return pathlib.PurePosixPath(f"/repos/{self.name}")

    @property
    def github(self) -> interface.IGithubAPI:
        return self._github

    @cached_property
    def issues(self) -> "interface.IGithubIssues":
        return self.github.issues_class(
            self.github,
            repo=self)

    @property
    def labels(self) -> "interface.IGithubIterator":
        return self.iter_entities(
            self.github.label_class, "labels")

    @property
    def name(self) -> str:
        return self._name

    async def commit(self, name: str) -> "interface.IGithubCommit":
        return self.github.commit_class(
            self,
            await self.getitem(f"commits/{name}"))

    def commits(self, since: datetime = None) -> "interface.IGithubIterator":
        query = "commits"
        if since is not None:
            query = f"{query}?since={utils.dt_to_js_isoformat(since)}"
        return self.getiter(
            query,
            inflate=partial(self.github.commit_class, self))

    async def create_release(
            self,
            branch: str,
            tag_name: str) -> Dict[str, str | Dict]:
        if await self.tag_exists(tag_name):
            raise exceptions.TagExistsError(
                f"Cannot create tag, already exists: {tag_name}")
        return await self.post(
            "releases",
            dict(tag_name=tag_name,
                 name=tag_name,
                 target_commitish=branch))

    async def getitem(self, query: str) -> Any:
        """Call the `gidgethub.getitem` api for this repo."""
        return await self.github.getitem(self.github_endpoint(query))

    def getiter(self, query: str, **kwargs) -> "interface.IGithubIterator":
        """Return a `GithubIterator` wrapping `gidgethub.getiter` for this
        repo."""
        return self.github.getiter(self.github_endpoint(query), **kwargs)

    def github_endpoint(self, rel_path: str) -> str:
        """Github API path for provided relative path."""
        return str(self.github_path.joinpath(rel_path))

    async def highest_release(
            self,
            since: Optional[datetime] = None) -> Optional[
                "interface.IGithubRelease"]:
        highest_release = None

        async for release in self.releases():
            if since and release.published_at < since:
                break
            is_higher = (
                not release.prerelease
                and release.version
                and (not highest_release
                     or (release.version >= highest_release.version)))
            if is_higher:
                highest_release = release
        return highest_release

    def iter_entities(
            self,
            entity: Type[base.GithubEntity],
            path: str,
            **kwargs) -> "interface.IGithubIterator":
        """Iterate and inflate entities for provided type."""
        return self.getiter(
            path,
            inflate=partial(entity, self),
            **kwargs)

    async def patch(self, query: str, data: Optional[Dict] = None) -> Any:
        return await self.github.patch(self.github_endpoint(query), data=data)

    async def post(
            self,
            query: str,
            data: Optional[Dict] = None, **kwargs) -> Any:
        return await self.github.post(
            self.github_endpoint(query),
            data=data,
            **kwargs)

    async def release(self, name: str) -> "interface.IGithubRelease":
        return self.github.release_class(
            self,
            await self.getitem(f"releases/tags/{name}"))

    def releases(self) -> "interface.IGithubIterator":
        """Iterate releases for this repo."""
        # TODO: make per_page configurable
        return self.iter_entities(
            self.github.release_class,
            "releases?per_page=100")

    async def tag(self, name: str) -> "interface.IGithubTag":
        ref_tag = await self.getitem(f"git/ref/tags/{name}")
        if ref_tag["object"]["type"] != "tag":
            raise exceptions.TagNotFound(name)
        tag = await self.github.getitem(ref_tag["object"]["url"])
        return self.github.tag_class(self, tag)

    async def tag_exists(self, tag_name: str) -> bool:
        try:
            await self.getitem(f"releases/tags/{tag_name}")
            return True
        except gidgethub.BadRequest:
            pass
        return False

    def tags(self) -> "interface.IGithubIterator":
        """Iterate tags for this repo."""
        return self.iter_entities(
            self.github.tag_class,
            "tags")
