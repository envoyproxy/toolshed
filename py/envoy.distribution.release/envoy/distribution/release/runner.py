
import gidgethub
import gidgethub.abc
from typing import TYPE_CHECKING

from aio.run import runner

from envoy.github.abstract import (
    GithubReleaseError, AGithubReleaseRunner, AGithubReleaseManager)
from envoy.github.release import manager


class ReleaseRunner(AGithubReleaseRunner):
    """This runner interacts with the Github release API to create, push, and
    fetch releases and release assets."""

    if TYPE_CHECKING:
        @property
        def command(self) -> runner.ACommand:
            return super().command

        @property
        def commands(self) -> runner.abstract.CommandDict:
            return super().commands

        @property
        def release_manager(self) -> AGithubReleaseManager:
            return super().release_manager

        def add_arguments(self, parser) -> None:
            super().add_arguments(parser)

    @property
    def release_manager_class(self) -> type[AGithubReleaseManager]:
        return manager.GithubReleaseManager

    @runner.cleansup
    @runner.catches(
        (gidgethub.GitHubException,
         GithubReleaseError,
         KeyboardInterrupt))
    async def run(self) -> int | None:
        return await super().run()


ReleaseRunner.__abstractmethods__ = frozenset()
