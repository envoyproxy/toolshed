
import asyncio
import pathlib
from datetime import datetime
from functools import cached_property
from typing import AsyncGenerator, List, Optional, Tuple, Type, Union

import aiohttp
from packaging import version as _version

import abstracts

from aio.api import github as _github

from envoy.base import utils
from envoy.base.utils import exceptions, interface, typing


DATE_FORMAT = "%B %-d, %Y"
ENVOY_REPO = "envoyproxy/envoy"
VERSION_PATH = "VERSION.txt"


@abstracts.implementer(interface.IProject)
class AProject(metaclass=abstracts.Abstraction):

    def __init__(
            self,
            path: Union[pathlib.Path, str] = ".",
            version: Optional[_version.Version] = None,
            github: Optional[_github.IGithubAPI] = None,
            repo: Optional[_github.IGithubRepo] = None,
            github_token: Optional[str] = None,
            session: Optional[aiohttp.ClientSession] = None) -> None:
        self._version = version
        self._path = path
        self._github = github
        self.github_token = github_token
        self._repo = repo
        self._session = session

    @cached_property
    def archived_versions(self) -> Tuple[_version.Version, ...]:
        non_archive = (5 if self.is_main_dev else 4)
        return tuple(
            reversed(
                sorted(self.minor_versions.keys())))[non_archive:]

    @cached_property
    def changelogs(self) -> interface.IChangelogs:
        return self.changelogs_class(self)

    @property  # type:ignore
    @abstracts.interfacemethod
    def changelogs_class(self) -> Type[interface.IChangelogs]:
        raise NotImplementedError

    @property
    def datestamp(self) -> str:
        return datetime.utcnow().date().strftime(DATE_FORMAT)

    @cached_property
    def dev_version(self) -> Optional[_version.Version]:
        return self.changelogs.current if self.is_dev else None

    @cached_property
    def github(self) -> _github.IGithubAPI:
        """Github API."""
        return self._github or _github.GithubAPI(
            self.session, "",
            oauth_token=self.github_token)

    @cached_property
    def inventories(self) -> interface.IInventories:
        return self.inventories_class(self)

    @property  # type:ignore
    @abstracts.interfacemethod
    def inventories_class(self) -> Type[interface.IInventories]:
        raise NotImplementedError

    @property
    def is_dev(self) -> bool:
        return self.version.is_devrelease

    @property
    def is_main_dev(self) -> bool:
        return self.is_dev and self.version.micro == 0

    @cached_property
    def minor_version(self) -> _version.Version:
        return utils.minor_version_for(self.version)

    @cached_property
    def minor_versions(self) -> typing.MinorVersionsDict:
        minor_versions: dict = {}
        for changelog_version in self.changelogs:
            minor_version = utils.minor_version_for(changelog_version)
            minor_versions[minor_version] = minor_versions.get(
                minor_version, [])
            minor_versions[minor_version].append(changelog_version)
        return {
            k: self._patch_versions(v)
            for k, v
            in minor_versions.items()}

    @cached_property
    def path(self) -> pathlib.Path:
        return pathlib.Path(self._path)

    @cached_property
    def repo(self) -> _github.IGithubRepo:
        return self._repo or self.github[ENVOY_REPO]

    @cached_property
    def session(self) -> aiohttp.ClientSession:
        """HTTP client session."""
        return self._session or aiohttp.ClientSession()

    @cached_property
    def stable_versions(self) -> Tuple[_version.Version, ...]:
        exclude = set(self.archived_versions)
        if self.is_main_dev:
            exclude.add(self.minor_version)
        return tuple(
            reversed(
                sorted(set(self.minor_versions.keys()) - exclude)))

    @cached_property
    def version(self) -> _version.Version:
        return (
            _version.Version(self.version_path.read_text().strip())
            if self._version is None
            else self._version)

    @cached_property
    def version_path(self) -> pathlib.Path:
        return self.path.joinpath(VERSION_PATH)

    def changes_for_commit(
            self,
            change: typing.ProjectChangeDict) -> Tuple[str, ...]:
        changed = set()
        if any(k in change for k in ["dev", "release"]):
            changed.add(VERSION_PATH)
        return tuple(
            sorted(
                changed
                | self.changelogs.changes_for_commit(change)
                | self.inventories.changes_for_commit(change)))

    async def commit(
            self,
            change: typing.ProjectChangeDict,
            msg: str) -> AsyncGenerator:
        changed = self.changes_for_commit(change)
        for path in changed:
            yield path
        await self._git_commit(changed, msg)

    async def dev(
            self,
            patch: bool = False) -> typing.ProjectDevResultDict:
        if self.is_dev:
            raise exceptions.DevError("Project is already set to dev")
        if self.changelogs.is_pending:
            raise exceptions.DevError(
                "Current changelog date is already set to `Pending`")
        new_version = utils.increment_version(self.version, patch=patch)
        self.write_version(new_version, dev=True)
        self.changelogs.write_version(self.version)
        self.changelogs.write_current()
        return dict(
            date="Pending",
            version=self.version_string(new_version, dev=True),
            old_version=self.version)

    def is_current(self, version: _version.Version) -> bool:
        return (
            self.version.base_version
            == version.base_version)

    async def release(self) -> typing.ProjectReleaseResultDict:
        if not self.is_dev:
            raise exceptions.ReleaseError(
                "Project is not set to dev")
        self.write_version(self.version)
        date = self.datestamp
        self.changelogs.write_date(date)
        return dict(
            date=date,
            version=self.version.base_version)

    async def sync(self) -> typing.ProjectSyncResultDict:
        results = await asyncio.gather(
            self.changelogs.sync(),
            self.inventories.sync())
        return dict(
            changelog=results[0],
            inventory=results[1])

    def version_string(
            self,
            version: _version.Version,
            dev: bool = False) -> str:
        dev_str = "-dev" if dev else ""
        return f"{version.base_version}{dev_str}"

    def write_version(
            self,
            version: _version.Version,
            dev: bool = False) -> None:
        self.version_path.write_text(
            f"{self.version_string(version, dev=dev)}\n")

    async def _exec(self, command: str) -> None:
        result = await asyncio.subprocess.create_subprocess_shell(
            command,
            cwd=self.path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE)
        stdout, stderr = await result.communicate()
        if result.returncode != 0:
            raise exceptions.CommitError(
                "\n".join([
                    stdout.decode("utf-8"),
                    stderr.decode("utf-8")]))

    async def _git_commit(self, changed: Tuple[str, ...], msg: str) -> None:
        await self._exec(
            " ".join(("git", "add", *changed)))
        await self._exec(
            " ".join(("git", "commit", *changed, "-m", f"'{msg}'")))

    def _patch_versions(
            self,
            versions: List[_version.Version]) -> Tuple[_version.Version, ...]:
        return tuple(
            reversed(
                sorted(
                    versions
                    if not self.is_dev
                    else (
                        v for v
                        in versions
                        if not self.is_current(v)))))
