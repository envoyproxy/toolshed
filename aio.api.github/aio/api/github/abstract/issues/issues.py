
import urllib
from functools import cached_property, partial
from typing import Any, Callable, Dict

import gidgethub

import abstracts

from aio.api.github import abstract, exceptions, interface


@abstracts.implementer(interface.IGithubIssue)
class AGithubIssue(
        abstract.base.GithubRepoEntity,
        metaclass=abstracts.Abstraction):
    """A Github issue."""

    def __gt__(self, other) -> bool:
        return self.number > other.number

    def __lt__(self, other) -> bool:
        return self.number < other.number

    def __str__(self):
        return f"<{self.__class__.__name__} {self.repo.name}#{self.number}>"

    @property
    def body(self) -> str:
        return self.data["body"]

    @property
    def number(self) -> int:
        return int(self.data["number"])

    @property
    def title(self) -> str:
        return self.data["title"]

    async def close(self) -> interface.IGithubIssue:
        return await self.edit(state="closed")

    async def comment(self, comment: str) -> Any:
        # TODO: add comment class
        return await self.repo.post(
            f"issues/{self.number}/comments", data=dict(body=comment))

    async def edit(self, **kwargs) -> interface.IGithubIssue:
        """Edit the issue."""
        return self.__class__(
            self.repo,
            await self.repo.patch(f"issues/{self.number}", data=kwargs))


@abstracts.implementer(interface.IGithubIssues)
class AGithubIssues(metaclass=abstracts.Abstraction):
    """Github issues."""

    def __init__(
            self,
            github: interface.IGithubAPI,
            repo: interface.IGithubRepo = None,
            filter: str = "") -> None:
        self._github = github
        self.repo = repo
        self._filter = filter

    @property
    def github(self) -> interface.IGithubAPI:
        return self._github

    @cached_property
    def filter(self) -> str:
        """Github search filter."""
        filter_parts = []
        if self._filter:
            filter_parts.append(self._filter)
        if self.repo:
            filter_parts.append(f"repo:{self.repo.name}")
        filters = " ".join(filter_parts)
        return filters and f"{filters} " or filters

    async def create(self, title: str, **kwargs) -> interface.IGithubIssue:
        repo = kwargs.pop("repo", None) or self.repo
        if not repo:
            raise exceptions.IssueCreateError(
                f"To create an issue, either `{self.__class__.__name__}` "
                "must be instantiated with a `repo` or `create` must be "
                "called with one.")
        kwargs["title"] = title
        try:
            data = await repo.post("issues", data=kwargs)
        except gidgethub.GitHubException as e:
            raise exceptions.IssueCreateError(
                f"Failed to create issue '{title}' in {repo.name}\n"
                f"Recieved: {e}")
        return self.github.issue_class(repo, data)

    def inflater(self, repo: interface.IGithubRepo = None) -> Callable:
        """Return default or custom callable to inflate a `GithubIssue`."""
        repo = repo or self.repo
        if not repo:
            return self._inflate
        return partial(self.github.issue_class, repo)

    def search(
            self,
            query: str,
            repo: interface.IGithubRepo = None) -> interface.IGithubIterator:
        return self.github.getiter(
            self.search_query(query),
            inflate=self.inflater(repo))

    def search_query(self, query: str) -> str:
        """Generate a search query."""
        q = urllib.parse.quote(f"{self.filter}{query}")
        return f"/search/issues?q={q}"

    def _inflate(self, result: Dict) -> interface.IGithubIssue:
        """Inflate an issue, finding the repo from the issue url."""
        return self.github.issue_class(
            self.github.repo_from_url(result["repository_url"]),
            result)
