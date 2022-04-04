
from typing import Any, Callable, Dict

from aio.api.github import interface


UNSET = object()


class GithubEntity:
    """Base Github entity class."""

    def __init__(self, github: interface.IGithubAPI, data: Dict) -> None:
        self._github = github
        self.data = data

    @property
    def github(self) -> "interface.IGithubAPI":
        """Github API."""
        return self._github

    @property
    def __data__(self) -> Dict[str, Callable]:
        """Dictionary of callables to mangle corresponding `self.data` keys."""
        return {}

    def __getattr__(self, k: str, default: Any = UNSET) -> Any:
        """Return the item from `self.data`, after mangling if required."""
        try:
            v = self.data[k]
        except KeyError:
            if default is not UNSET:
                return default
            return self.__getattribute__(k)
        return self.__data__.get(k, lambda x: x)(v)


class GithubRepoEntity(GithubEntity):
    """Base Github repo entity class."""

    def __init__(self, repo: interface.IGithubRepo, data: Dict) -> None:
        self.repo = repo
        self.data = data

    @property
    def github(self) -> interface.IGithubAPI:
        """Github API."""
        return self.repo.github
