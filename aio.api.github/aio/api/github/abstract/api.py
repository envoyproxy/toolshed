
import abc
from functools import cached_property
from typing import Any, Type

import gidgethub
import gidgethub.abc
import gidgethub.aiohttp

import abstracts

from .commit import AGithubCommit
from .issues import AGithubIssue, AGithubIssues
from .iterator import AGithubIterator
from .label import AGithubLabel
from .release import AGithubRelease
from .repo import AGithubRepo
from .tag import AGithubTag


class AGithubAPI(metaclass=abstracts.Abstraction):
    """Github API wrapper.

    Can be used to access the gidgethub API directly.

    Can also be used to work with repos by calling `self["repo/name"]`.
    """

    def __init__(self, *args, **kwargs) -> None:
        self.args = args
        self.kwargs = kwargs

    def __getitem__(self, k) -> AGithubRepo:
        """Return a `GithubRepository` for `k`"""
        # TODO: make this work with user and organization
        #  and validate `k`
        return self.repo_class(self, k)

    @cached_property
    def api(self) -> gidgethub.abc.GitHubAPI:
        """Gidgethub API."""
        return self.api_class(*self.args, **self.kwargs)

    @property
    @abc.abstractmethod
    def api_class(self) -> Type[gidgethub.abc.GitHubAPI]:
        """API class."""
        return gidgethub.aiohttp.GitHubAPI

    @property  # type:ignore
    @abstracts.interfacemethod
    def commit_class(self) -> Type[AGithubCommit]:
        """Github commit class."""
        raise NotImplementedError

    @property  # type:ignore
    @abstracts.interfacemethod
    def label_class(self) -> Type[AGithubLabel]:
        """Github label class."""
        raise NotImplementedError

    @property  # type:ignore
    @abstracts.interfacemethod
    def issue_class(self) -> Type[AGithubIssue]:
        """Github issue class."""
        raise NotImplementedError

    @property  # type:ignore
    @abstracts.interfacemethod
    def issues_class(self) -> Type[AGithubIssues]:
        """Github issues class."""
        raise NotImplementedError

    @property  # type:ignore
    @abstracts.interfacemethod
    def iterator_class(self) -> Type[AGithubIterator]:
        """Github iterator class.

        Provides both an async iterator and a `total_count` async prop.
        """
        raise NotImplementedError

    @property  # type:ignore
    @abstracts.interfacemethod
    def release_class(self) -> Type[AGithubRelease]:
        """Github release class."""
        raise NotImplementedError

    @property  # type:ignore
    @abstracts.interfacemethod
    def repo_class(self) -> Type[AGithubRepo]:
        """Github repo class."""
        raise NotImplementedError

    @property  # type:ignore
    @abstracts.interfacemethod
    def tag_class(self) -> Type[AGithubTag]:
        """Github tag class."""
        raise NotImplementedError

    async def getitem(self, *args, **kwargs) -> Any:
        """Call the `gidgethub.getitem` api."""
        # print("GETITEM", args, kwargs)
        return await self.api.getitem(*args, **kwargs)

    def getiter(self, *args, **kwargs) -> AGithubIterator:
        """Return a `GithubIterator` wrapping `gidgethub.getiter`."""
        # print("GETITER", args, kwargs)
        return self.iterator_class(self.api, *args, **kwargs)

    async def patch(self, *args, **kwargs):
        """Call the `gidgethub.patch` api."""
        # print("PATCH", args, kwargs)
        return await self.api.patch(*args, **kwargs)

    async def post(self, *args, **kwargs):
        """Call the `gidgethub.post` api."""
        # print("POST", args, kwargs)
        return await self.api.post(*args, **kwargs)

    def repo_from_url(self, url):
        """Return the corresponding `GithubRepo` for an api url."""
        repo_url = f"{self.api.base_url}/repos/"
        if not url.startswith(repo_url):
            return None
        return self["/".join(url[len(repo_url):].split("/")[:2])]
