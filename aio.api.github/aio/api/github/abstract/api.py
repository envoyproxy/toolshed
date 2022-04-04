
import abc
from functools import cached_property
from typing import Any, Type

import aiohttp

import gidgethub
import gidgethub.aiohttp

import abstracts

from aio.api.github import interface


@abstracts.implementer(interface.IGithubAPI)
class AGithubAPI(metaclass=abstracts.Abstraction):
    """Github API wrapper.

    Can be used to access the gidgethub API directly.

    Can also be used to work with repos by calling `self["repo/name"]`.
    """

    def __init__(
            self,
            session: aiohttp.ClientSession,
            *args, **kwargs) -> None:
        self._session = session
        self.args = args
        self.kwargs = kwargs

    def __getitem__(self, k) -> interface.IGithubRepo:
        # TODO: make this work with user and organization
        #  and validate `k`
        return self.repo_class(self, k)

    @cached_property
    def api(self) -> gidgethub.aiohttp.GitHubAPI:
        """Gidgethub API."""
        return self.api_class(
            self.session,
            *self.args,
            **self.kwargs)

    @property
    @abc.abstractmethod
    def api_class(self) -> Type[gidgethub.aiohttp.GitHubAPI]:
        """API class."""
        return gidgethub.aiohttp.GitHubAPI

    @property  # type:ignore
    @abstracts.interfacemethod
    def commit_class(self) -> Type[interface.IGithubCommit]:
        raise NotImplementedError

    @property  # type:ignore
    @abstracts.interfacemethod
    def issue_class(self) -> Type[interface.IGithubIssue]:
        raise NotImplementedError

    @property  # type:ignore
    @abstracts.interfacemethod
    def issues_class(self) -> Type[interface.IGithubIssues]:
        raise NotImplementedError

    @property  # type:ignore
    @abstracts.interfacemethod
    def iterator_class(self) -> Type[interface.IGithubIterator]:
        """Github iterator class.

        Provides both an async iterator and a `total_count` async prop.
        """
        raise NotImplementedError

    @property  # type:ignore
    @abstracts.interfacemethod
    def label_class(self) -> Type[interface.IGithubLabel]:
        raise NotImplementedError

    @property  # type:ignore
    @abstracts.interfacemethod
    def release_class(self) -> Type[interface.IGithubRelease]:
        raise NotImplementedError

    @property  # type:ignore
    @abstracts.interfacemethod
    def repo_class(self) -> Type[interface.IGithubRepo]:
        """Github repo class."""
        raise NotImplementedError

    @property
    def session(self) -> aiohttp.ClientSession:
        return self._session

    @property  # type:ignore
    @abstracts.interfacemethod
    def tag_class(self) -> Type[interface.IGithubTag]:
        raise NotImplementedError

    async def getitem(self, *args, **kwargs) -> Any:
        # print("GETITEM", args, kwargs)
        return await self.api.getitem(*args, **kwargs)

    def getiter(self, *args, **kwargs) -> interface.IGithubIterator:
        # print("GETITER", args, kwargs)
        return self.iterator_class(self.api, *args, **kwargs)

    async def patch(self, *args, **kwargs):
        # print("PATCH", args, kwargs)
        return await self.api.patch(*args, **kwargs)

    async def post(self, *args, **kwargs):
        # print("POST", args, kwargs)
        return await self.api.post(*args, **kwargs)

    def repo_from_url(self, url):
        repo_url = f"{self.api.base_url}/repos/"
        if not url.startswith(repo_url):
            return None
        return self["/".join(url[len(repo_url):].split("/")[:2])]
