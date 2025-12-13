
import argparse
from functools import cached_property
from typing import Optional, Type

import gidgethub
import gidgethub.abc

from aio.run import runner

from envoy.github.abstract import (
    GithubReleaseError, AGithubReleaseRunner, AGithubReleaseManager)
from envoy.github.release import manager


class ReleaseRunner(AGithubReleaseRunner):
    """This runner interacts with the Github release API to create, push, and
    fetch releases and release assets."""

    @cached_property
    def command(self) -> runner.ACommand:
        return super().command

    @cached_property
    def commands(self) -> runner.abstract.CommandDict:
        return super().commands

    @cached_property
    def release_manager(self) -> AGithubReleaseManager:
        return super().release_manager

    @property
    def release_manager_class(self) -> Type[AGithubReleaseManager]:
        return manager.GithubReleaseManager

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        super().add_arguments(parser)

    @runner.cleansup
    @runner.catches(
        (gidgethub.GitHubException,
         GithubReleaseError,
         KeyboardInterrupt))
    async def run(self) -> Optional[int]:
        return await super().run()
