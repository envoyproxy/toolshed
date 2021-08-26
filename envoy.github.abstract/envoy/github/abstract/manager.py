import pathlib
from abc import abstractmethod
from functools import cached_property
from typing import (
    Dict, List,
    Optional, Union)

import verboselogs  # type:ignore

import packaging.version

import aiohttp

import gidgethub.abc

import abstracts

from aio.functional import async_property

from .release import AGithubRelease


class AGithubReleaseManager(metaclass=abstracts.Abstraction):
    """This utility wraps the github API to provide the ability to
    create and manage releases and release assets.

    A github client connection and/or aiohttp session can be provided if you
    wish to reuse the client or session.

    If you do not provide a session, one will be created and the async
    `.close()` method should called after use.

    For this reason, instances of this class can be used as an async
    contextmanager, and the session will be automatically closed on exit, for
    example:

    ```python

    from tools.github.release.manager import GithubReleaseManager

    async with GithubReleaseManager(...) as manager:
        await manager["1.19.0"].create()
    ```
    """

    @abstractmethod
    async def __aenter__(self) -> "AGithubReleaseManager":
        raise NotImplementedError

    @abstractmethod
    async def __aexit__(self, *args) -> None:
        raise NotImplementedError

    @abstractmethod
    def __getitem__(self, version) -> AGithubRelease:
        """Accessor for a specific Github release"""
        raise NotImplementedError

    @cached_property
    @abstractmethod
    def github(self) -> gidgethub.abc.GitHubAPI:
        """An instance of the gidgethub GitHubAPI"""
        raise NotImplementedError

    @async_property
    @abstractmethod
    async def latest(self) -> Dict[str, packaging.version.Version]:
        """Returns a dictionary of latest minor and patch versions

        For example, given the following versions:

        1.19.2, 1.19.1, 1.20.3

        It would return:

        1.19 -> 1.19.2
        1.19.1 -> 1.19.1
        1.19.2 -> 1.19.2
        1.20 -> 1.20.3
        1.20.3 -> 1.20.3

        """
        raise NotImplementedError

    @cached_property
    @abstractmethod
    def log(self) -> verboselogs.VerboseLogger:
        """A verbose logger"""
        raise NotImplementedError

    @async_property
    @abstractmethod
    async def releases(self) -> List[Dict]:
        """List of dictionaries containing information about available releases,
        as returned by the Github API
        """
        raise NotImplementedError

    @cached_property
    @abstractmethod
    def releases_url(self) -> pathlib.PurePosixPath:
        """Github API releases URL"""
        raise NotImplementedError

    @cached_property
    @abstractmethod
    def session(self) -> aiohttp.ClientSession:
        """Aiohttp Client session, also used for Github API client"""
        raise NotImplementedError

    @abstractmethod
    def fail(self, message: str) -> str:
        """Either raise an error or log a warning and return the message,
        dependent on the value of `self.continues`.
        """
        raise NotImplementedError

    @abstractmethod
    def format_version(
            self,
            version: Union[str, packaging.version.Version]) -> str:
        """Formatted version name - eg `1.19.0` -> `v1.19.0`"""
        raise NotImplementedError

    @abstractmethod
    def parse_version(
            self, version: str) -> Optional[packaging.version.Version]:
        """Parsed version - eg `v1.19.0` -> `Version(1.19.0)`"""
        raise NotImplementedError
