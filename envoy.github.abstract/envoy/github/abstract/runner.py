
import abc
import argparse
import pathlib
from typing import Optional, Type

import abstracts

from aio.run import runner

from .manager import AGithubReleaseManager


class AGithubReleaseRunner(
        runner.ARunnerWithCommands,
        metaclass=abstracts.Abstraction):

    @property
    def continues(self) -> bool:
        return getattr(self.args, "continue")

    @property
    def oauth_token(self) -> str:
        no_token = (
            not self.oauth_token_file
            or not self.oauth_token_file.exists())
        if no_token:
            return ""
        return self.oauth_token_file.read_text().strip()  # type:ignore

    @property
    def oauth_token_file(self) -> Optional[pathlib.Path]:
        if not getattr(self.args, "oauth_token_file", None):
            return None
        return pathlib.Path(self.args.oauth_token_file)

    @property
    def path(self) -> pathlib.Path:
        return pathlib.Path(self.tempdir.name)

    @property
    @abc.abstractmethod
    def release_manager(self) -> AGithubReleaseManager:
        return self.release_manager_class(
            self.path,
            self.repository,
            log=self.log,
            oauth_token=self.oauth_token,
            continues=self.continues)

    @property  # type:ignore
    @abstracts.interfacemethod
    def release_manager_class(self) -> Type[AGithubReleaseManager]:
        raise NotImplementedError

    @property
    def repository(self) -> str:
        return self.args.repository

    @abc.abstractmethod
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
        parser.add_argument(
            "command",
            choices=self.commands.keys(),
            help="Command to run")

    async def cleanup(self) -> None:
        if "release_manager" in self.__dict__:
            await self.release_manager.close()
            del self.__dict__["release_manager"]
        await super().cleanup()
