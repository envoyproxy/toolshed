import argparse
import json
import logging
import pathlib
import shutil
from functools import cached_property
from itertools import chain
from typing import List, Set, Tuple

import abstracts

import aio.core.subprocess
from aio.core.functional import async_property

from .abstract import ARepoManager
from .exceptions import RepoError


class DebRepoError(RepoError):
    pass


class AptlyError(RepoError):
    pass


class AAptly(metaclass=abstracts.Abstraction):

    @property  # type:ignore
    @abstracts.interfacemethod
    def aptly_command(self) -> pathlib.Path:
        """Path to the `aptly` command."""
        raise NotImplementedError

    @async_property(cache=True)
    async def aptly_config(self) -> dict:
        """Aptly configuration."""
        return json.loads(await self.aptly("config", "show"))

    @async_property
    async def aptly_root_dir(self) -> pathlib.Path:
        """Aptly root directory."""
        return pathlib.Path((await self.aptly_config)["rootDir"])

    @property  # type:ignore
    @abstracts.interfacemethod
    def log(self) -> logging.Logger:
        raise NotImplementedError

    @async_property
    async def aptly_repos(self) -> List[str]:
        """Created aptly repositories."""
        return (
            await self.aptly(
                "repo", "list",
                "-raw")).strip().split("\n")

    @async_property
    async def aptly_snapshots(self) -> List[str]:
        """Created aptly snapshots."""
        return (
            await self.aptly(
                "snapshot", "list",
                "-raw")).strip().split("\n")

    @async_property
    async def aptly_published(self) -> List[str]:
        """Created aptly publishings."""
        return list(
            r.split(" ")[1]
            for r
            in (await self.aptly(
                "publish", "list",
                "-raw")).strip().split("\n"))

    async def aptly(self, *args: str) -> str:
        """Run an aptly command."""
        command = (self.aptly_command, ) + args
        result = await aio.core.subprocess.run(
            command, capture_output=True, encoding="utf-8")

        if result.returncode:
            raise AptlyError(
                f"Error running aptly ({command}):\n{result.stderr}")

        if result.stderr.strip():
            self.log.info(result.stderr)

        return result.stdout


class DebRepoManager(ARepoManager, AAptly):
    file_types = r".*(\.deb|\.changes)$"

    @classmethod
    def add_arguments(cls, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("--deb_aptly_command", nargs="?")

    def __init__(self, *args, **kwargs) -> None:
        self._aptly_command = kwargs.pop("aptly_command", None)
        ARepoManager.__init__(self, *args, **kwargs)

    @cached_property
    def aptly_command(self) -> pathlib.Path:
        command = self._aptly_command or shutil.which("aptly")
        if not command:
            raise DebRepoError(
                "Unable to find aptly command, and none provided")
        command = pathlib.Path(command)
        if not command.exists():
            raise DebRepoError(
                f"Unable to find aptly command: {command}")
        return command

    @cached_property
    def changes_files(self) -> Tuple[pathlib.Path, ...]:
        """Debian changes files to include."""
        return tuple(
            x for x
            in self.path.glob(f"**/{self.name}/*.changes"))

    @cached_property
    def distros(self) -> Set[str]:
        """Configured distributions - eg `buster`, `bullseye`"""
        return set(chain.from_iterable(self.versions.values()))

    async def create_distro(self, distro: str) -> None:
        """Create an aptly distribution repository."""
        if await self.distro_exists(distro):
            await self.drop_distro(distro)
        self.log.notice(f"Creating deb distribution: {distro}")
        self.log.success(
            (await self.aptly(
                "repo", "create",
                f"-distribution=\"{distro}\"",
                "-component=main",
                distro)).strip().split("\n")[0])

    async def create_snapshot(self, distro: str) -> None:
        """Create an aptly snapshot."""
        if await self.snapshot_exists(distro):
            await self.drop_snapshot(distro)
        self.log.success(
            (await self.aptly(
                "snapshot", "create",
                distro, "from", "repo", distro)).strip())

    async def distro_exists(self, distro: str) -> bool:
        """Given aptly repository distribution has already been created."""
        return bool(distro in await self.aptly_repos)

    async def drop_distro(self, distro: str) -> None:
        """Given aptly repository distribution has already been created."""
        self.log.warning(f"Removing existing repo {distro}")
        await self.aptly("repo", "drop", "-force", distro)

    async def drop_published(self, distro: str) -> None:
        """Drop an aptly distribution publishing."""
        self.log.warning(f"Removing existing published version {distro}")
        await self.aptly("publish", "drop", distro)

    async def drop_snapshot(self, distro: str) -> None:
        """Drop an aptly snapshot."""
        self.log.warning(f"Removing existing snapshot {distro}")
        if await self.published_exists(distro):
            await self.drop_published(distro)
        await self.aptly("snapshot", "drop", "-force", distro)

    async def include_changes(self, distro: str) -> None:
        """Include configured changes files."""
        for changes_file in self.changes_files:
            await self.include_changes_file(distro, changes_file)

    async def include_changes_file(
            self,
            distro: str,
            changes_file: pathlib.Path) -> None:
        """Include a changes files to a distribution."""
        if not str(changes_file).endswith(f".{distro}.changes"):
            return
        self.log.success(
            (await self.aptly(
                "repo", "include",
                "-no-remove-files",
                str(changes_file))).strip().split("\n")[-1])

    async def publish(self) -> pathlib.Path:
        self.log.notice("Building deb repository")
        for distro in self.distros:
            await self.publish_distro(distro)
        return await self.aptly_root_dir

    async def publish_distro(self, distro: str) -> None:
        """Publish a configured distribution."""
        await self.create_distro(distro)
        await self.include_changes(distro)
        await self.create_snapshot(distro)
        await self.publish_snapshot(distro)

    async def publish_snapshot(self, distro: str) -> None:
        """Publish a snapshot."""
        self.log.info(
            await self.aptly(
                "publish", "snapshot",
                f"-distribution={distro}",
                f"-architectures={','.join(self.architectures)}",
                distro))

    async def published_exists(self, distro: str) -> bool:
        """Publishing for a distribution exists already."""
        return bool(distro in await self.aptly_published)

    async def snapshot_exists(self, snapshot: str) -> bool:
        """Snapshot exists already."""
        return bool(snapshot in await self.aptly_snapshots)
