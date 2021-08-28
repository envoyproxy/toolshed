
import argparse
import pathlib
import re
from functools import cached_property
from typing import Dict, Optional, List, Pattern

from aio.functional import async_property

from envoy.base import command
from envoy.github.abstract import (
    AGithubRelease, AGithubReleaseManager)


class ReleaseCommand(command.Command):

    @cached_property
    def manager(self) -> AGithubReleaseManager:
        return self.runner.release_manager

    @cached_property
    def release(self) -> AGithubRelease:
        return self.manager[self.version]

    @property
    def version(self) -> str:
        return self.args.version

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        super().add_arguments(parser)
        parser.add_argument("version", help="Version to retrieve assets for")

    def format_response(
            self,
            release: Optional[Dict] = None,
            assets: Optional[List[Dict]] = None,
            errors: Optional[List[Dict]] = None) -> str:
        for k, v in (release or {}).items():
            if isinstance(v, dict):
                print(k)
                for _k, _v in v.items():
                    _k = f"{k}.{_k}"
                    print('{0:<30} {1}'.format(_k, _v or ""))
                continue
            if isinstance(v, list):
                continue
            print('{0:<30} {1}'.format(k, v or ""))
        for i, result in enumerate(assets or []):
            k = "assets" if i == 0 else ""
            print('{0:<30} {1:<30} {2}'.format(
                k, result["name"], result["url"]))


class ListCommand(ReleaseCommand):

    async def run(self) -> None:
        releases = await self.runner.release_manager.list_releases()
        for release in releases:
            self.runner.stdout.info(release["tag_name"])


class ReleaseSubcommand(command.Subcommand):

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        super().add_arguments(parser)
        parser.add_argument("version", help="Version to retrieve assets for")


class AssetsCommand(ReleaseCommand):

    async def run(self) -> None:
        assets = await self.release.assets
        if not assets:
            self.runner.log.warning(f"Version {self.version} has no assets")
            return
        for asset in assets:
            self.runner.stdout.info(asset["name"])


class FetchCommand(ReleaseCommand):

    @property
    def asset_types(self) -> Dict[str, Pattern]:
        return {
            t.split(":", 1)[0]: re.compile(t.split(":", 1)[1])
            for t in self.args.asset_type or []}

    @property
    def path(self) -> pathlib.Path:
        return pathlib.Path(self.args.path)

    @property
    def find_latest(self) -> bool:
        return any(release.count(".") < 2 for release in self.versions)

    @async_property(cache=True)
    async def releases(self) -> Dict[str, AGithubRelease]:
        return (
            {str((await self.manager.latest)[version]): self.manager[
                str((await self.manager.latest)[version])]
             for version in self.versions}
            if self.find_latest
            else {version: self.manager[version] for version in self.versions})

    @property
    def versions(self) -> List[str]:
        return self.args.version

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        command.Command.add_arguments(self, parser)
        parser.add_argument(
            "version",
            nargs="*",
            help="Version to retrieve assets for")
        parser.add_argument(
            "--path",
            help=(
                "Path to save assets to, can either be a directory "
                "or a tarball path"))
        parser.add_argument(
            "--asset-type",
            nargs="*",
            help="Regex to match asset type and folder to fetch asset into")

    async def run(self) -> None:
        for i, release in enumerate((await self.releases).values()):
            await release.fetch(self.path, self.asset_types, append=(i != 0))


class PushCommand(ReleaseCommand):

    @property
    def paths(self) -> List[pathlib.Path]:
        return [pathlib.Path(path) for path in self.args.assets]

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        super().add_arguments(parser)
        parser.add_argument(
            "--assets",
            nargs="*",
            help=(
                "Path to push assets from, can either be a directory "
                "or a tarball"))

    async def run(self) -> None:
        await self.release.push(self.paths)


class CreateCommand(ReleaseCommand):

    @property
    def assets(self) -> List[pathlib.Path]:
        return [pathlib.Path(asset) for asset in self.args.assets or []]

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        super().add_arguments(parser)
        parser.add_argument(
            "--assets",
            nargs="*",
            help="Regex to match asset type and folder to fetch asset into")

    async def run(self) -> None:
        result = await self.release.create(assets=self.assets)
        self.format_response(
            release=result["release"],
            assets=result.get("assets"),
            errors=result.get("errors"))


class DeleteCommand(ReleaseCommand):

    async def run(self) -> None:
        await self.release.delete()


class InfoCommand(ReleaseCommand):

    async def run(self) -> None:
        self.format_response(await self.release.release)
