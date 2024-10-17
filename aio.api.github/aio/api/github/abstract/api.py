
import abc
from functools import cached_property
from typing import Any

import aiohttp

import gidgethub
import gidgethub.abc
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

    @property
    @abstracts.interfacemethod
    def actions_class(self) -> type[interface.IGithubActions]:
        raise NotImplementedError

    @cached_property
    def api(self) -> gidgethub.aiohttp.GitHubAPI:
        """Gidgethub API."""
        return self.api_class(
            self.session,
            *self.args,
            **self.kwargs)

    @property
    @abc.abstractmethod
    def api_class(self) -> type[gidgethub.aiohttp.GitHubAPI]:
        """API class."""
        return gidgethub.aiohttp.GitHubAPI

    @property
    @abstracts.interfacemethod
    def commit_class(self) -> type[interface.IGithubCommit]:
        raise NotImplementedError

    @property
    @abstracts.interfacemethod
    def issue_class(self) -> type[interface.IGithubIssue]:
        raise NotImplementedError

    @property
    @abstracts.interfacemethod
    def issues_class(self) -> type[interface.IGithubIssues]:
        raise NotImplementedError

    @property
    @abstracts.interfacemethod
    def iterator_class(self) -> type[interface.IGithubIterator]:
        """Github iterator class.

        Provides both an async iterator and a `total_count` async prop.
        """
        raise NotImplementedError

    @property
    @abstracts.interfacemethod
    def label_class(self) -> type[interface.IGithubLabel]:
        raise NotImplementedError

    @property
    @abstracts.interfacemethod
    def release_class(self) -> type[interface.IGithubRelease]:
        raise NotImplementedError

    @property
    @abstracts.interfacemethod
    def repo_class(self) -> type[interface.IGithubRepo]:
        """Github repo class."""
        raise NotImplementedError

    @property
    def session(self) -> aiohttp.ClientSession:
        return self._session

    @property
    @abstracts.interfacemethod
    def tag_class(self) -> type[interface.IGithubTag]:
        raise NotImplementedError

    @property
    @abstracts.interfacemethod
    def workflows_class(self) -> type[interface.IGithubWorkflows]:
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
        if url.startswith(repo_url := f"{self.api.base_url}/repos/"):
            return self["/".join(url[len(repo_url):].split("/")[:2])]
