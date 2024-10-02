import pathlib
from functools import cached_property
from typing import (
    Dict, Iterable,
    Optional, Pattern, Set, Tuple, Type)

import verboselogs  # type:ignore

import aiohttp

import gidgethub.abc
import gidgethub.aiohttp

import abstracts

from aio.core.tasks import ConcurrentError
from aio.core.functional import async_property

from envoy.github.abstract import (
    AGithubAction, AGithubActionAssetsFetcher,
    AGithubActionAssetsPusher, AGithubActionManager,
    GithubActionError, ActionDict)
from envoy.github.action.assets import (
    GithubActionAssetsFetcher, GithubActionAssetsPusher)


@abstracts.implementer(AGithubAction)
class GithubAction:
    file_exts = {"deb", "changes", "rpm"}

    def __init__(self, manager: AGithubActionManager, version: str):
        self.manager = manager
        self._version = version

    @async_property(cache=True)
    async def asset_names(self) -> Set[str]:
        """Set of the names of assets for this action version."""
        return set(asset["name"] for asset in await self.assets)

    @async_property(cache=True)
    async def assets(self) -> Dict:
        """Assets dictionary as returned by Github Action API."""
        try:
            return await self.github.getitem(await self.assets_url)
        except gidgethub.GitHubException as e:
            raise GithubActionError(e)

    @async_property(cache=True)
    async def assets_url(self) -> str:
        """URL for retrieving this version's assets information from."""
        return (await self.action)["assets_url"]

    @async_property(cache=True)
    async def delete_url(self) -> pathlib.PurePosixPath:
        """Github API-relative URL for deleting this action version."""
        return self.actions_url.joinpath(str(await self.action_id))

    @async_property
    async def exists(self) -> bool:
        return self.version_name in await self.action_names

    @property
    def fetcher(self) -> Type[AGithubActionAssetsFetcher]:
        return GithubActionAssetsFetcher

    @property
    def github(self) -> gidgethub.abc.GitHubAPI:
        return self.manager.github

    @property
    def log(self) -> verboselogs.VerboseLogger:
        return self.manager.log

    @property
    def pusher(self) -> Type[AGithubActionAssetsPusher]:
        return GithubActionAssetsPusher

    @async_property(cache=True)
    async def action(self) -> Dict:
        """Dictionary of action version information as returned by the Github
        Action API."""
        return await self.get()

    @async_property(cache=True)
    async def action_id(self) -> int:
        """The Github action ID for this version, required for some URLs."""
        return (await self.action)["id"]

    @async_property
    async def action_names(self) -> Tuple[str, ...]:
        """Tuple of action tag names as returned by the Github Action API.

        This is used to check whether the action exists already.
        """
        return tuple(
            action["tag_name"]
            for action
            in await self.manager.actions)

    @property
    def actions_url(self) -> pathlib.PurePosixPath:
        return self.manager.actions_url

    @property
    def session(self) -> aiohttp.ClientSession:
        return self.manager.session

    @async_property(cache=True)
    async def upload_url(self) -> str:
        """Upload URL for this action version."""
        return (await self.action)["upload_url"].split("{")[0]

    @property
    def version(self) -> str:
        return self._version

    @property
    def version_name(self) -> str:
        return self.manager.format_version(self.version)

    @cached_property
    def version_url(self) -> pathlib.PurePosixPath:
        """Github API-relative URL to retrieve action version information
        from."""
        return self.actions_url.joinpath("tags", self.version_name)

    async def create(
            self,
            assets: Optional[Iterable[pathlib.Path]] = None) -> ActionDict:
        results = ActionDict()
        if await self.exists:
            self.fail(f"Action {self.version_name} already exists")
        else:
            self.log.notice(f"Creating action {self.version}")
            try:
                results["action"] = await self.github.post(
                    str(self.actions_url),
                    data=dict(tag_name=self.version_name))
            except gidgethub.GitHubException as e:
                raise GithubActionError(e)
            self.log.success(f"Action created {self.version}")
        if assets:
            results.update(await self.push(assets))
        return results

    async def delete(self) -> None:
        if not await self.exists:
            raise GithubActionError(
                f"Unable to delete version {self.version_name} as it does not "
                "exist")
        self.log.notice(f"Deleting action version: {self.version_name}")
        try:
            await self.github.delete(str(await self.delete_url))
        except gidgethub.GitHubException as e:
            raise GithubActionError(e)
        self.log.success(f"Action version deleted: {self.version_name}")

    async def fetch(
            self,
            path: pathlib.Path,
            asset_types: Optional[Dict[str, Pattern[str]]] = None,
            append: Optional[bool] = False) -> ActionDict:
        self.log.notice(
            "Downloading assets for action version: "
            f"{self.version_name} -> {path}")
        response = ActionDict(assets=[], errors=[])
        fetcher = self.fetcher(self, path, asset_types, append=append)
        async for result in fetcher:
            if result.get("error"):
                response["errors"].append(result)
                continue
            response["assets"].append(result)
            self.log.info(
                f"Asset saved: {result['name']} -> {result['outfile']}")
        if not response["errors"]:
            self.log.success(
                "Assets downloaded for action version: "
                f"{self.version_name} -> {path}")
        return response

    def fail(self, message: str) -> str:
        return self.manager.fail(message)

    async def get(self) -> Dict:
        try:
            return await self.github.getitem(str(self.version_url))
        except gidgethub.GitHubException as e:
            raise GithubActionError(e)

    async def push(
            self,
            artefacts: Iterable[pathlib.Path]) -> ActionDict:
        self.log.notice(f"Pushing assets for {self.version}")
        response = ActionDict(assets=[], errors=[])
        try:
            for path in artefacts:
                async for result in self.pusher(self, path):
                    if result.get("error"):
                        response["errors"].append(result)
                        continue
                    response["assets"].append(result)
                    self.log.info(f"Action file uploaded {result['name']}")
        except ConcurrentError as e:
            raise e.args[0]
        if not response["errors"]:
            self.log.success(f"Assets uploaded: {self.version}")
        return response
