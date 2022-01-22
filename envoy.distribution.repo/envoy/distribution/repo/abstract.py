
import argparse
import logging
import pathlib
import re
from abc import abstractmethod
from functools import cached_property
from typing import Dict, List, Optional, Pattern, Type, TypedDict

import verboselogs  # type:ignore

import abstracts

from aio.core.functional import async_property

from envoy.base import runner, utils

from .exceptions import RepoError


PUBLISH_YAML = "publish.yaml"


class ReleaseConfigDict(TypedDict):
    repo: str
    file_types: Dict[str, str]
    architectures: List
    versions: Dict[str, Dict[str, List[str]]]


class ARepoBuildingRunner(
        runner.AsyncRunner,
        metaclass=abstracts.Abstraction):
    _repo_types = ()

    @classmethod
    def register_repo_type(cls, name: str, util: Type["ARepoManager"]) -> None:
        """Register a repo type."""
        cls._repo_types = (
            getattr(cls, "_repo_types")
            + ((name, util),))

    @cached_property
    def asset_types(self) -> Dict[str, Pattern[str]]:
        """Dictionary of names to asset type patterns."""
        return {
            k: re.compile(v.file_types)
            for k, v in self.repo_types.items()}

    @cached_property
    def path(self) -> pathlib.Path:
        """Temp directory path."""
        return pathlib.Path(self.tempdir.name)

    @cached_property
    def release_config(self) -> ReleaseConfigDict:
        """Release configuration."""
        if not self.release_config_file.exists():
            raise RepoError(
                "Unable to find release configuration: "
                f"{self.release_config_file}")
        try:
            return utils.typed(
                ReleaseConfigDict,
                utils.from_yaml(self.release_config_file))
        except utils.TypeCastingError:
            raise RepoError(
                "Unable to parse release configuration: "
                f"{self.release_config_file}")

    @property
    def release_config_file(self) -> pathlib.Path:
        """Path to the release configuration file."""
        return pathlib.Path(PUBLISH_YAML)

    @cached_property
    def repo_types(self) -> Dict[str, Type["ARepoManager"]]:
        """Registered repository types."""
        return dict(self._repo_types)

    @cached_property
    def repos(self) -> Dict[str, "ARepoManager"]:
        """Dictionary of instances of the registered repository types."""
        return {
            repo_type: manager(
                repo_type,
                self.path,
                self.release_config,
                self.log,
                self.stdout,
                **self._kwargs_for_type(repo_type))
            for repo_type, manager
            in self.repo_types.items()}

    @async_property
    async def published_repos(self):
        """Generator of paths from publishing repos."""
        for repo in self.repos.values():
            yield await repo.publish()

    @abstractmethod
    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        super().add_arguments(parser)
        for manager in self.repo_types.values():
            manager.add_arguments(parser)

    async def cleanup(self):
        await super().cleanup()

    @abstracts.interfacemethod
    async def run(self) -> Optional[int]:
        raise NotImplementedError

    def _kwargs_for_type(self, repo_type: str) -> dict:
        return {
            k[len(repo_type) + 1:]: v
            for k, v in vars(self.args).items()
            if k.startswith(f"{repo_type}_")}


class ARepoManager(metaclass=abstracts.Abstraction):
    file_types: str = r"^$"

    @classmethod
    @abstracts.interfacemethod
    def add_arguments(cls, parser: argparse.ArgumentParser) -> None:
        raise NotImplementedError

    def __init__(
            self,
            name: str,
            path: pathlib.Path,
            config: ReleaseConfigDict,
            log: verboselogs.VerboseLogger,
            stdout: logging.Logger,
            **kwargs) -> None:
        self.name: str = name
        self.path = path
        self.config = config
        self._log = log
        self.stdout = stdout

    @cached_property
    def architectures(self) -> List[str]:
        """Supported architectures."""
        return self.config["architectures"]

    @property
    def log(self) -> verboselogs.VerboseLogger:
        return self._log

    @property
    def versions(self) -> Dict[str, List[str]]:
        """Versions configured for this repository type."""
        return {
            k: v[self.name]
            for k, v
            in self.config["versions"].items()
            if self.name in v}

    @abstractmethod
    async def publish(self) -> pathlib.Path:
        """Publish a repository."""
        raise NotImplementedError
