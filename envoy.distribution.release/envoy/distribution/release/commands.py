
import argparse
import pathlib
import re
from typing import Dict, List, Optional, Pattern

from aio.core.functional import async_property

import abstracts

from envoy.github.abstract import AGithubRelease, AGithubReleaseCommand


@abstracts.implementer(AGithubReleaseCommand)
class AssetsCommand:

    async def run(self) -> Optional[int]:
        assets = await self.release.assets
        if not assets:
            self.runner.log.warning(f"Version {self.version} has no assets")
            return 1
        for asset in assets:
            self.runner.stdout.info(asset["name"])


@abstracts.implementer(AGithubReleaseCommand)
class CreateCommand:

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        super().add_arguments(parser)
        parser.add_argument(
            "--assets",
            nargs="*",
            help=(
                "Path to push assets from, can either be a directory "
                "or a tarball"))

    async def run(self) -> Optional[int]:
        return self.format_response(
            **await self.release.create(assets=self.artefacts))


@abstracts.implementer(AGithubReleaseCommand)
class DeleteCommand:

    async def run(self) -> Optional[int]:
        return await self.release.delete()


@abstracts.implementer(AGithubReleaseCommand)
class InfoCommand:

    async def run(self) -> Optional[int]:
        return self.format_response(await self.release.release)


@abstracts.implementer(AGithubReleaseCommand)
class ListCommand:

    async def run(self) -> Optional[int]:
        for release in await self.runner.release_manager.releases:
            self.runner.stdout.info(release["tag_name"])


@abstracts.implementer(AGithubReleaseCommand)
class FetchCommand:

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
        if self.find_latest:
            latest = await self.manager.latest
            return {
                str(latest[version]): self.manager[str(latest[version])]
                for version in self.versions}
        return {
            version: self.manager[version]
            for version in self.versions}

    @property
    def versions(self) -> List[str]:
        return self.args.version

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "version",
            nargs="*",
            help=(
                "Version to retrieve assets for. "
                "Can be specified multiple times"))
        parser.add_argument(
            "--path",
            help=(
                "Path to save assets to, can either be a directory "
                "or a tarball path"))
        parser.add_argument(
            "--asset-type",
            nargs="*",
            help="Regex to match asset type and folder to fetch assets into")

    async def run(self) -> Optional[int]:
        for i, release in enumerate((await self.releases).values()):
            await release.fetch(self.path, self.asset_types, append=(i != 0))


@abstracts.implementer(AGithubReleaseCommand)
class PushCommand:

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        super().add_arguments(parser)
        parser.add_argument(
            "--assets",
            nargs="*",
            help=(
                "Path to push assets from, can either be a directory "
                "or a tarball"))

    async def run(self) -> Optional[int]:
        await self.release.push(self.artefacts)
