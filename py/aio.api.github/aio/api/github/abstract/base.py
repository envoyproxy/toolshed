
from typing import Any, Callable

from aio.api.github import interface


UNSET = object()


# TODO: clean this up - use an abstraction

class GithubEntity:
    """Base Github entity class."""

    def __init__(self, repo: interface.IGithubRepo, data: dict) -> None:
        self.data = data
        self._repo = repo

    @property
    def __data__(self) -> dict[str, Callable]:
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

    @property
    def github(self) -> interface.IGithubAPI:
        """Github API."""
        return self.repo.github

    @property
    def repo(self) -> interface.IGithubRepo:
        """Github API."""
        return self._repo


class GithubRepoEntity(GithubEntity):
    """Base Github repo entity class."""

    def __init__(self, repo: interface.IGithubRepo, data: dict) -> None:
        self.data = data
        self._repo = repo
