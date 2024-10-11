
import abstracts
import argparse
import os
import pathlib
from functools import cached_property
from typing import Callable

import aiohttp

import gidgethub
import gidgethub.abc
import gidgethub.aiohttp

from aio.api import github as _github
from aio.run import runner

from envoy.ci.report import interface


ENV_GITHUB_TOKEN = "GITHUB_TOKEN"
ENVOY_REPO = "envoyproxy/envoy"
IGNORED_WORKFLOWS = ["Command"]
IGNORED_TRIGGERS = ["pull_request_target"]


class AReportRunner(
        runner.Runner,
        metaclass=abstracts.Abstraction):

    @property
    def filters(self) -> dict[str, str]:
        return {
            filter_name: filter_string
            for filter_name, filter_class in self.registered_filters.items()
            if (filter_string := str(filter_class(self.args)))}

    @cached_property
    def github(self) -> _github.IGithubAPI:
        """Github API."""
        return _github.GithubAPI(
            self.session, "",
            oauth_token=self.github_token)

    @property
    def github_token(self) -> str | None:
        """Github access token."""
        if self.args.github_token:
            return pathlib.Path(self.args.github_token).read_text().strip()
        return os.getenv(ENV_GITHUB_TOKEN)

    @property
    def ignored_triggers(self) -> list[str]:
        return self.args.ignored_triggers.split(",")

    @property
    def ignored_workflows(self) -> list[str]:
        return self.args.ignored_workflows.split(",")

    @cached_property
    def format(self) -> Callable:
        return (
            _format()
            if (_format := self.registered_formats.get(self.args.format))
            else None)

    @property
    @abstracts.interfacemethod
    def registered_filters(self) -> dict:
        raise NotImplementedError

    @property
    @abstracts.interfacemethod
    def registered_formats(self) -> dict:
        raise NotImplementedError

    @cached_property
    def repo(self) -> _github.IGithubRepo:
        return self.github[self.repo_name]

    @property
    def repo_name(self) -> str:
        return self.args.repo

    @cached_property
    def runs(self) -> interface.ICIRuns:
        return self.runs_class(
            self.repo,
            filters=self.filters,
            ignored=dict(
                workflows=self.ignored_workflows,
                triggers=self.ignored_triggers),
            sort_ascending=(self.args.sort == "asc"))

    @property
    @abstracts.interfacemethod
    def runs_class(self) -> type[interface.ICIRuns]:
        raise NotImplementedError

    @cached_property
    def session(self) -> aiohttp.ClientSession:
        """HTTP client session."""
        return aiohttp.ClientSession()

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        super().add_arguments(parser)
        # parser.add_argument("--end")
        # parser.add_argument("--start")
        parser.add_argument("--github_token")
        parser.add_argument("--repo", default=ENVOY_REPO)
        group = parser.add_mutually_exclusive_group()
        group.add_argument(
            "--current",
            choices=["hour", "day", "week", None],
            default=None)
        group.add_argument(
            "--previous",
            choices=["hour", "day", "week", None],
            default=None)
        parser.add_argument(
            "--ignored_triggers",
            default=",".join(IGNORED_TRIGGERS))
        parser.add_argument(
            "--ignored_workflows",
            default=",".join(IGNORED_WORKFLOWS))
        parser.add_argument(
            "-s", "--status",
            choices=["all", "failure"],
            default="all")
        parser.add_argument(
            "--sort",
            choices=["asc", "desc"],
            default="desc")
        parser.add_argument(
            "-f", "--format",
            default="json",
            choices=self.registered_formats.keys())

    @runner.cleansup
    @runner.catches(
        (gidgethub.GitHubException,
         KeyboardInterrupt))
    async def run(self) -> int | None:
        self.format(await self.runs.as_dict)
