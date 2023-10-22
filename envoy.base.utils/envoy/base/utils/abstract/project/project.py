
import asyncio
import json
import pathlib
from concurrent import futures
from functools import cached_property
from typing import (
    AsyncGenerator, AsyncIterator, List, Mapping, Optional,
    Tuple, Type, Union)

import aiohttp
from packaging import version as _version

import abstracts

from aio.api import github as _github
from aio.core import directory as _directory, event
from aio.core.functional import async_property, AwaitableGenerator

from envoy.base import utils
from envoy.base.utils import exceptions, interface, typing


ENVOY_REPO = "envoyproxy/envoy"
MAIN_BRANCH = "main"
VERSION_PATH = "VERSION.txt"


@abstracts.implementer(interface.IProject)
class AProject(event.AExecutive, metaclass=abstracts.Abstraction):

    def __init__(
            self,
            path: Union[pathlib.Path, str] = ".",
            version: Optional[_version.Version] = None,
            github: Optional[_github.IGithubAPI] = None,
            repo: Optional[str | _github.IGithubRepo] = None,
            github_token: Optional[str] = None,
            session: Optional[aiohttp.ClientSession] = None,
            loop: Optional[asyncio.AbstractEventLoop] = None,
            pool: Optional[futures.Executor] = None) -> None:
        self._version = version
        self._path = path
        self._github = github
        self.github_token = github_token
        self._repo = repo
        self._session = session
        self._loop = loop
        self._pool = pool

    @cached_property
    def archived_versions(self) -> Tuple[_version.Version, ...]:
        # This assumes that the previous changelogs are present and correct
        # eg. if you remove some of the recent changelogs its assumption
        # will break, and it will detect the wrong versions as stable/archived
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

    @cached_property
    def dev_version(self) -> Optional[_version.Version]:
        return self.changelogs.current if self.is_dev else None

    @cached_property
    def directory(self) -> _directory.ADirectory:
        """Greppable directory - optionally in a git repo, depending on whether
        we want to look at all files.
        """
        return self.directory_class(self.path, **self.directory_kwargs)

    @property  # type:ignore
    @abstracts.interfacemethod
    def directory_class(self) -> Type[_directory.ADirectory]:
        raise NotImplementedError

    @property
    def directory_kwargs(self) -> Mapping:
        return dict(
            pool=self.pool,
            loop=self.loop)

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
    def is_main(self) -> bool:
        return self.version.micro == 0

    @property
    def is_main_dev(self) -> bool:
        return self.is_dev and self.is_main

    @async_property
    async def json_data(self) -> str:
        """JSON representation of project data."""
        return json.dumps(
            dict(
                version=str(self.version),
                version_string=self.version_string(
                    self.version,
                    self.version.dev is not None),
                stable_versions=tuple(
                    str(v)
                    for v
                    in self.stable_versions),
                releases=tuple(
                    release.data["tag_name"]
                    for release
                    in await AwaitableGenerator(
                        self.repo.releases()))))

    @property
    def main_branch(self) -> str:
        return MAIN_BRANCH

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
        if isinstance(self._repo, _github.IGithubRepo):
            return self._repo
        if self._repo:
            return self.github[self._repo]
        return self.github[ENVOY_REPO]

    @property
    def rel_version_path(self) -> pathlib.Path:
        return pathlib.Path(VERSION_PATH)

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
        return self.path.joinpath(self.rel_version_path)

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
            msg: str,
            author: Optional[str] = None) -> AsyncGenerator:
        changed = self.changes_for_commit(change)
        for path in changed:
            yield path
        await self._git_commit(changed, msg, author)

    async def dev(
            self,
            patch: bool = False) -> typing.ProjectDevResultDict:
        if self.is_dev:
            raise exceptions.DevError("Project is already set to dev")
        if await self.changelogs.is_pending:
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

    async def publish(
            self,
            dry_run: bool = False,
            assets: Optional[pathlib.Path] = None,
            commitish: Optional[str] = None,
            publish_commit_message: Optional[bool] = None,
            dev: Optional[bool] = None,
            latest: Optional[bool] = None) -> AsyncIterator[
                typing.ProjectPublishResultDict
                | _github.typing.AssetUploadResultDict]:
        if not dev and self.is_dev and not dry_run:
            raise _github.exceptions.TagError(
                f"Cannot tag a dev version: {self.version}")
        commit_message: Optional[str] = None
        if publish_commit_message:
            commit = await self.repo.commit(commitish)
            commit_message = (
                commit.data[0]
                if not commitish
                else commit.data)["commit"]["message"]
        commitish = (
            commitish
            if commitish
            else (self.main_branch
                  if self.is_main
                  else f"release/v{self.minor_version}"))
        latest = latest or (self.is_main and not self.is_dev)
        release = await self.repo.create_release(
            commitish,
            f"v{self.version}",
            latest=latest,
            body=commit_message,
            dry_run=dry_run)
        yield dict(
            commitish=release.target_commitish,
            body=commit_message or "",
            date=release.published_at.isoformat(),
            tag_name=release.tag_name,
            url=release.html_url,
            dry_run=" (dry run)" if dry_run else "")
        if not assets:
            return
        with utils.untar(assets) as tmpdir:
            tasks = release.assets.push(
                tmpdir.joinpath("bin"),
                dry_run=dry_run)
            async for result in tasks:
                yield result

    async def release(self) -> typing.ProjectReleaseResultDict:
        if not self.is_dev:
            raise exceptions.ReleaseError(
                "Project is not set to dev")
        self.write_version(self.version)
        date = self.changelogs.datestamp
        await self.changelogs.write_date(date)
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

    async def trigger(self, **kwargs) -> typing.ProjectTriggerResultDict:
        await self.repo.actions.workflows.dispatch(**kwargs)
        return dict(
            workflow=kwargs["workflow"])

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

    async def _git_commit(
            self,
            changed: Tuple[str, ...],
            msg: str,
            author: Optional[str] = None) -> None:
        author_args = (
            ["--author", f"'{author}'"]
            if author
            else [])
        await self._exec(
            " ".join(("git", "add", *changed)))
        await self._exec(
            " ".join((
                "git", "commit", *author_args, *changed,
                "-m", f"'{msg}'")))

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
