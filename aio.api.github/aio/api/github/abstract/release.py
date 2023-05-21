
import logging
import pathlib
from datetime import datetime
from functools import cached_property
from typing import AsyncIterator, Callable, Dict, Optional, Type

from packaging import version

import abstracts

from aio.api.github import interface, typing, utils
from aio.core.tasks import concurrent
from .base import GithubRepoEntity


logger = logging.getLogger(__name__)


@abstracts.implementer(interface.IGithubRelease)
class AGithubRelease(GithubRepoEntity, metaclass=abstracts.Abstraction):
    """A Github release."""

    @classmethod
    async def create(
            cls,
            repo: interface.IGithubRepo,
            data: dict,
            dry_run: bool = False) -> interface.IGithubRelease:
        if not dry_run:
            data = await repo.post("releases", data)
        else:
            release_url = f"test://releases/{data['tag_name']}"
            data.update(
                dict(published_at=datetime.now().isoformat(),
                     upload_url=f"{release_url}/upload",
                     html_url=release_url))
        return cls(repo, data)

    @cached_property
    def __data__(self) -> Dict[str, Callable]:
        return dict(
            created_at=utils.dt_from_js_isoformat,
            published_at=utils.dt_from_js_isoformat)

    def __str__(self):
        return f"<{self.__class__.__name__} {self.repo.name}@{self.tag_name}>"

    @cached_property
    def assets(self) -> interface.IGithubReleaseAssets:
        return self.assets_class(self)

    @property  # type: ignore
    @abstracts.interfacemethod
    def assets_class(self) -> Type[interface.IGithubReleaseAssets]:
        raise NotImplementedError

    @property
    def tag_name(self) -> str:
        return self.data["tag_name"]

    @property
    def upload_url(self) -> str:
        return self.data["upload_url"]

    @cached_property
    def version(self) -> Optional[version.Version]:
        try:
            return version.parse(self.tag_name)
        except version.InvalidVersion:
            return None


@abstracts.implementer(interface.IGithubReleaseAssets)
class AGithubReleaseAssets(metaclass=abstracts.Abstraction):
    """Base class for Github release assets pusher/fetcher."""
    _concurrency = 4

    def __init__(
            self,
            release: "interface.IGithubRelease") -> None:
        self._release = release

    @property
    def release(self) -> "interface.IGithubRelease":
        return self._release

    @property
    def upload_url(self) -> str:
        return self.release.upload_url.split("{")[0]

    def artefact_url(self, name: str) -> str:
        """URL to upload a provided artefact name as an asset."""
        return f"{self.upload_url}?name={name}"

    async def push(
            self,
            path: pathlib.Path,
            dry_run=False) -> AsyncIterator[dict]:
        awaitables = (
            self.upload(p, self.artefact_url(p.name), dry_run=dry_run)
            for p
            in path.glob("*"))
        async for result in concurrent(awaitables, limit=self._concurrency):
            yield result

    async def upload(
            self,
            artefact: pathlib.Path,
            url: str,
            dry_run: bool = False) -> typing.AssetUploadResultDict:
        """Upload an artefact from a filepath to a given URL."""
        response = (
            await self.release.repo.post(
                url,
                data=artefact.read_bytes(),
                content_type="application/octet-stream")
            if not dry_run
            else dict(state="uploaded",
                      url=(f"test://releases/{self.release.tag_name}"
                           f"/assets/{artefact.name}")))
        errored = (
            response.get("error")
            or not response.get("state") == "uploaded")
        result: typing.AssetUploadResultDict = dict(
            name=artefact.name,
            url=(response["url"]
                 if not errored
                 else url))
        if errored:
            result["error"] = response
        else:
            logger.debug(
                f"Upload {'(dry run) ' if dry_run else ''}release "
                f"({self.release.tag_name}): {artefact.name}")
        return result
