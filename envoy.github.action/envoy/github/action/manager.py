import pathlib
import re
from functools import cached_property
from typing import Dict, List, Optional, Pattern, Type, Union

import verboselogs  # type:ignore

import packaging.version

import aiohttp

import gidgethub.abc
import gidgethub.aiohttp

import abstracts
from aio.core.functional import async_property

from envoy.github.abstract import (
    AGithubAction, AGithubActionManager, GithubActionError)
from envoy.github.action.action import GithubAction


@abstracts.implementer(AGithubActionManager)
class GithubActionManager:

    _version_re = r"v(\w+)"
    _version_format = "v{version}"

    async def __aenter__(self) -> AGithubActionManager:
        return self

    async def __aexit__(self, *args) -> None:
        await self.close()

    def __getitem__(self, version) -> AGithubAction:
        return self.action_class(self, version)

    @property
    def action_class(self) -> Type[AGithubAction]:
        return GithubAction

    @cached_property
    def github(self) -> gidgethub.abc.GitHubAPI:
        return (
            self._github
            or gidgethub.aiohttp.GitHubAPI(
                self.session,
                self.user,
                oauth_token=self.oauth_token))

    @cached_property
    def log(self) -> verboselogs.VerboseLogger:
        return self._log or verboselogs.VerboseLogger(__name__)

    @cached_property
    def path(self) -> pathlib.Path:
        return pathlib.Path(self._path)

    @async_property
    async def latest(self) -> Dict[str, packaging.version.Version]:
        latest = {}
        for action in await self.actions:
            version = self.parse_version(action["tag_name"])
            if not version:
                continue
            latest[str(version)] = version
            minor = f"{version.major}.{version.minor}"
            if version > latest.get(minor, self.version_min):
                latest[minor] = version
        return latest

    @async_property
    async def actions(self) -> List[Dict]:
        results = []
        async for result in self.github.getiter(str(self.actions_url)):
            results.append(result)
        return results

    @cached_property
    def actions_url(self) -> pathlib.PurePosixPath:
        return pathlib.PurePosixPath(f"/repos/{self.repository}/actions")

    @cached_property
    def session(self) -> aiohttp.ClientSession:
        return self._session or aiohttp.ClientSession()

    @cached_property
    def version_re(self) -> Pattern[str]:
        return re.compile(self._version_re)

    def fail(self, message: str) -> str:
        if not self.continues:
            raise GithubActionError(message)
        self.log.warning(message)
        return message

    def format_version(
            self,
            version: Union[str, packaging.version.Version]) -> str:
        return self._version_format.format(version=version)

    def parse_version(
            self,
            version: str) -> Optional[packaging.version.Version]:
        _version = self.version_re.sub(r"\1", version)
        if _version:
            try:
                return packaging.version.Version(_version)
            except packaging.version.InvalidVersion:
                pass
        self.log.warning(f"Unable to parse version: {version}")
