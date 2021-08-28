
import argparse
import pathlib
import tarfile
from functools import cached_property
from typing import Dict, Optional, Pattern, Type

import gidgethub
import gidgethub.abc

from envoy.base import command, runner
from envoy.github.release import manager as github_release


class BaseReleaseRunner(command.AsyncRunnerWithCommands):

    @property
    def asset_types(self) -> Optional[Dict[str, Pattern[str]]]:
        return None

    @property
    def continues(self) -> bool:
        return getattr(self.args, "continue")

    @cached_property
    def create_releases(self) -> bool:
        return False

    @property
    def github(self) -> Optional[gidgethub.abc.GitHubAPI]:
        return None

    @property
    def oauth_token(self) -> str:
        if not self.oauth_token_file:
            return ""
        if not self.oauth_token_file.exists():
            return ""
        return self.oauth_token_file.read_text().strip()

    @property
    def oauth_token_file(self) -> Optional[pathlib.Path]:
        if not getattr(self.args, "oauth_token_file", None):
            return None
        return pathlib.Path(self.args.oauth_token_file)

    @property
    def path(self) -> pathlib.Path:
        return pathlib.Path(self.tempdir.name)

    @property
    def release_config(self) -> Dict[str, Optional[Dict[str, list]]]:
        raise NotImplementedError

    @property
    def release_manager_class(
            self) -> Type[github_release.GithubReleaseManager]:
        return github_release.GithubReleaseManager

    @cached_property
    def release_managers(
            self) -> Dict[str, github_release.GithubReleaseManager]:
        return {
            version: self.release_manager_class(
                self.path,
                self.repository,
                version=version,
                log=self.log,
                create=self.create_releases,
                github=self.github,
                user=self.user,
                oauth_token=self.oauth_token,
                asset_types=self.asset_types,
                continues=self.continues)
            for version in self.release_config}

    @cached_property
    def release_manager(self) -> github_release.GithubReleaseManager:
        return self.release_manager_class(
            self.path,
            self.repository,
            log=self.log,
            create=self.create_releases,
            github=self.github,
            user=self.user,
            oauth_token=self.oauth_token,
            asset_types=self.asset_types,
            continues=self.continues)

    @property
    def repository(self) -> str:
        return self.args.repository

    @property
    def user(self) -> str:
        return getattr(self.args, "user", "foo")

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        super().add_arguments(parser)
        parser.add_argument(
            "repository",
            help="Github repository")
        parser.add_argument(
            "oauth_token_file",
            help="Path to an OAuth token credentials file")
        parser.add_argument(
            "--continue",
            action="store_true",
            help="Continue if an indidividual github action fails")

    async def cleanup(self) -> None:
        if "release_manager" in self.__dict__:
            await self.release_manager.close()
            del self.__dict__["release_manager"]
        if "release_managers" in self.__dict__:
            for manager in self.release_managers.values():
                await manager.close()
        await super().cleanup()

    def create_archive(self, *paths) -> None:
        if not self.args.archive:
            return
        with tarfile.open(self.args.archive, "w") as tar:
            for path in paths:
                if path:
                    tar.add(path, arcname=".")


class ReleaseRunner(BaseReleaseRunner):
    """This runner interacts with the Github release API to build
    distribution repositories (eg apt/yum).
    """

    @cached_property
    def release_config(self) -> Dict[str, Optional[Dict[str, list]]]:
        if self.version:
            return {version: None for version in self.version}
        return {}

    @cached_property
    def version(self) -> str:
        return self.args.version

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        super().add_arguments(parser)
        parser.add_argument(
            "command",
            choices=self.commands.keys(),
            help="Command to run")
        # parser.add_argument(
        #   "version", nargs="*", help="Version to specify for some commands")

    @runner.cleansup
    @runner.catches(
        (gidgethub.GitHubException,
         github_release.GithubReleaseError,
         KeyboardInterrupt))
    async def run(self) -> Optional[int]:
        await super().run()
