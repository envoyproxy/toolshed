
from datetime import datetime
from typing import (
    Any, AsyncGenerator,
    Pattern, Type)

from packaging import version

import gidgethub.abc

import abstracts

import aiohttp


class IGithubCommit(metaclass=abstracts.Interface):
    pass


class IGithubLabel(metaclass=abstracts.Interface):
    pass


class IGithubRelease(metaclass=abstracts.Interface):

    @property  # type:ignore
    @abstracts.interfacemethod
    def repo(self) -> str:
        raise NotImplementedError

    @property  # type:ignore
    @abstracts.interfacemethod
    def tag_name(self) -> str:
        raise NotImplementedError

    @property  # type:ignore
    @abstracts.interfacemethod
    def upload_url(self) -> str:
        raise NotImplementedError

    @property  # type:ignore
    @abstracts.interfacemethod
    def version(self) -> version.Version | None:
        raise NotImplementedError


class IGithubReleaseAssets(metaclass=abstracts.Interface):

    @abstracts.interfacemethod
    def __init__(self, release: "IGithubRelease", name: str) -> None:
        raise NotImplementedError


class IGithubTag(metaclass=abstracts.Interface):
    pass


class IGithubIterator(metaclass=abstracts.Interface):

    @abstracts.interfacemethod
    async def __aiter__(self) -> AsyncGenerator[Any, None]:
        """Async iterate an API call, inflating the results."""
        if False:
            yield
        raise NotImplementedError

    @property  # type:ignore
    @abstracts.interfacemethod
    async def total_count(self) -> int:
        """Get `total_count` without iterating all items."""
        raise NotImplementedError


class IGithubAPI(metaclass=abstracts.Interface):

    @abstracts.interfacemethod
    def __getitem__(self, k: str) -> "IGithubRepo":
        """Return a `GithubRepository` for `k`"""
        raise NotImplementedError

    @property  # type:ignore
    @abstracts.interfacemethod
    def api(self) -> Type[gidgethub.abc.GitHubAPI]:
        """Github API."""
        raise NotImplementedError

    @property  # type:ignore
    @abstracts.interfacemethod
    def actions_class(self) -> Type["IGithubActions"]:
        """Github actions class."""
        raise NotImplementedError

    @property  # type:ignore
    @abstracts.interfacemethod
    def commit_class(self) -> Type["IGithubCommit"]:
        """Github commit class."""
        raise NotImplementedError

    @property  # type:ignore
    @abstracts.interfacemethod
    def issue_class(self) -> Type["IGithubIssue"]:
        """Github issue class."""
        raise NotImplementedError

    @property  # type:ignore
    @abstracts.interfacemethod
    def issues_class(self) -> Type["IGithubIssues"]:
        """Github issues class."""
        raise NotImplementedError

    @property  # type:ignore
    @abstracts.interfacemethod
    def label_class(self) -> Type["IGithubLabel"]:
        """Github label class."""
        raise NotImplementedError

    @property  # type:ignore
    @abstracts.interfacemethod
    def release_class(self) -> Type["IGithubRelease"]:
        """Github release class."""
        raise NotImplementedError

    @property  # type:ignore
    @abstracts.interfacemethod
    def session(self) -> aiohttp.ClientSession:
        raise NotImplementedError

    @property  # type:ignore
    @abstracts.interfacemethod
    def tag_class(self) -> Type["IGithubTag"]:
        """Github tag class."""
        raise NotImplementedError

    @abstracts.interfacemethod
    def getiter(self, *args, **kwargs) -> IGithubIterator:
        """Return a `GithubIterator` wrapping `gidgethub.getiter`."""
        raise NotImplementedError

    @abstracts.interfacemethod
    async def getitem(self, *args, **kwargs) -> Any:
        """Call the `gidgethub.getitem` api."""
        raise NotImplementedError

    @abstracts.interfacemethod
    def repo_from_url(self, url: str) -> "IGithubRepo":
        """Return the corresponding `GithubRepo` for an api url."""
        raise NotImplementedError

    @abstracts.interfacemethod
    async def patch(self, *args, **kwargs) -> Any:
        """Call the `gidgethub.patch` api."""
        raise NotImplementedError

    @abstracts.interfacemethod
    async def post(self, *args, **kwargs) -> Any:
        """Call the `gidgethub.post` api."""
        raise NotImplementedError

    @property  # type:ignore
    @abstracts.interfacemethod
    def workflows_class(self) -> Type["IGithubWorkflows"]:
        """Github workflows class."""
        raise NotImplementedError


class IGithubRepo(metaclass=abstracts.Interface):

    @abstracts.interfacemethod
    def __init__(self, github: "IGithubAPI", name: str) -> None:
        raise NotImplementedError

    @property  # type:ignore
    @abstracts.interfacemethod
    def actions(self) -> "IGithubActions":
        raise NotImplementedError

    @property  # type:ignore
    @abstracts.interfacemethod
    def github(self) -> IGithubAPI:
        raise NotImplementedError

    @property  # type:ignore
    @abstracts.interfacemethod
    def issues(self) -> "IGithubIssues":
        """Github issues for this repo."""
        raise NotImplementedError

    @property  # type:ignore
    @abstracts.interfacemethod
    def labels(self) -> IGithubIterator:
        """Github labels for this repo."""
        raise NotImplementedError

    @property  # type:ignore
    @abstracts.interfacemethod
    def name(self) -> str:
        raise NotImplementedError

    @abstracts.interfacemethod
    async def commit(self, name: str) -> "IGithubCommit":
        """Fetch a commit for this repo."""
        raise NotImplementedError

    @abstracts.interfacemethod
    def commits(self, since: datetime | None = None) -> IGithubIterator:
        """Iterate commits for this repo."""
        raise NotImplementedError

    @abstracts.interfacemethod
    async def create_release(
            self,
            commitish: str,
            name: str) -> dict[str, str | dict]:
        """Create a release for this repo."""
        raise NotImplementedError

    @abstracts.interfacemethod
    def getitem(self, *args, **kwargs) -> Any:
        """Call the `gidgethub.getitem` api for a repo."""
        raise NotImplementedError

    @abstracts.interfacemethod
    def getiter(self, *args, **kwargs) -> IGithubIterator:
        """Return a `GithubIterator` wrapping `gidgethub.getiter` for a
        repo."""
        raise NotImplementedError

    @abstracts.interfacemethod
    async def highest_release(
            self,
            since: datetime | None = None) -> IGithubRelease | None:
        """Release with the highest semantic version, optionally `since` a
        previous release date.

        Not necessarily the most recent.
        """
        raise NotImplementedError

    @abstracts.interfacemethod
    async def patch(self, query: str, data: dict | None = None) -> Any:
        """Call the `gidgethub.patch` api for this repo."""
        raise NotImplementedError

    @abstracts.interfacemethod
    async def post(self, query: str, data: dict | None = None) -> Any:
        """Call the `gidgethub.post` api for this repo."""
        raise NotImplementedError

    @abstracts.interfacemethod
    async def release(self, name: str) -> "IGithubRelease":
        """Fetch a release for this repo."""
        raise NotImplementedError

    @abstracts.interfacemethod
    async def releases(self, name: str) -> "IGithubIterator":
        """Fetch releases for this repo."""
        raise NotImplementedError

    @abstracts.interfacemethod
    async def tag(self, name: str) -> "IGithubTag":
        """Fetch a tag for this repo."""
        raise NotImplementedError

    @abstracts.interfacemethod
    async def tag_exists(self, tag_name: str) -> str:
        """Check whether a tag already exists."""
        raise NotImplementedError


class IGithubIssue(metaclass=abstracts.Interface):

    @property  # type:ignore
    @abstracts.interfacemethod
    def body(self) -> str:
        """Issue body."""
        raise NotImplementedError

    @property  # type:ignore
    @abstracts.interfacemethod
    def number(self) -> str:
        """Issue number."""
        raise NotImplementedError

    @property  # type:ignore
    @abstracts.interfacemethod
    def title(self) -> str:
        """Issue title."""
        raise NotImplementedError

    @abstracts.interfacemethod
    async def close(self) -> "IGithubIssue":
        """Close this issue."""
        raise NotImplementedError

    @abstracts.interfacemethod
    async def comment(self, comment: str) -> Any:
        """Add a comment to this issue."""
        raise NotImplementedError


class IGithubActions(metaclass=abstracts.Interface):

    @property  # type:ignore
    @abstracts.interfacemethod
    def github(self) -> IGithubAPI:
        """Github API."""
        raise NotImplementedError

    @property  # type:ignore
    @abstracts.interfacemethod
    def repo(self) -> IGithubRepo:
        """Github repo."""
        raise NotImplementedError


class IGithubWorkflows(metaclass=abstracts.Interface):

    @property  # type:ignore
    @abstracts.interfacemethod
    def github(self) -> IGithubAPI:
        """Github API."""
        raise NotImplementedError

    @property  # type:ignore
    @abstracts.interfacemethod
    def repo(self) -> IGithubRepo:
        """Github repo."""
        raise NotImplementedError


class IGithubIssues(metaclass=abstracts.Interface):

    @abstracts.interfacemethod
    async def create(self, title: str, **kwargs) -> IGithubIssue:
        """Create an issue."""
        raise NotImplementedError

    @abstracts.interfacemethod
    def search(
            self,
            query: str,
            repo: IGithubRepo | None = None) -> IGithubIterator:
        """Search for issues."""
        raise NotImplementedError


class IGithubTrackedIssue(metaclass=abstracts.Interface):

    @abstracts.interfacemethod
    def __init__(
            self,
            issues: "IGithubTrackedIssues",
            issue: "IGithubIssue") -> None:
        raise NotImplementedError

    @property  # type:ignore
    @abstracts.interfacemethod
    def body(self) -> str:
        """Github issue body."""
        raise NotImplementedError

    @property  # type:ignore
    @abstracts.interfacemethod
    def closing_tpl(self) -> str:
        """String template for closing comment."""
        raise NotImplementedError

    @property  # type:ignore
    @abstracts.interfacemethod
    def key(self) -> str | None:
        """Issue key."""
        raise NotImplementedError

    @property  # type:ignore
    @abstracts.interfacemethod
    def number(self) -> int:
        """Github issue number."""
        raise NotImplementedError

    @property  # type:ignore
    @abstracts.interfacemethod
    def parsed(self) -> dict[str, str]:
        """Parsed vars from issue title."""
        raise NotImplementedError

    @property  # type:ignore
    @abstracts.interfacemethod
    def repo_name(self) -> str:
        """Github repo name."""
        raise NotImplementedError

    @property  # type:ignore
    @abstracts.interfacemethod
    def title(self) -> str:
        """Github issue title."""
        raise NotImplementedError

    @abstracts.interfacemethod
    async def close(self) -> IGithubIssue:
        """Close this issue."""
        raise NotImplementedError

    @abstracts.interfacemethod
    async def close_duplicate(
            self,
            old_issue: "IGithubTrackedIssue") -> None:
        """Close a duplicate issue of this one."""
        raise NotImplementedError

    @abstracts.interfacemethod
    async def comment(self, comment: str) -> Any:
        """Comment on this issue."""
        raise NotImplementedError


class IGithubTrackedIssues(metaclass=abstracts.Interface):
    """Associated Github issues for a specific problem type."""

    @abstracts.interfacemethod
    def __init__(
            self,
            github: IGithubAPI,
            issue_author: str | None = None,
            repo_name: str | None = None) -> None:
        raise NotImplementedError

    @abstracts.interfacemethod
    async def __aiter__(
            self) -> AsyncGenerator[
                IGithubTrackedIssue,
                IGithubIssue]:
        """Iterate matching issues."""
        if False:
            yield
        raise NotImplementedError

    @property  # type:ignore
    @abstracts.interfacemethod
    def closing_tpl(self) -> str:
        """String template for closing comment."""
        raise NotImplementedError

    @property  # type:ignore
    @abstracts.interfacemethod
    async def duplicate_issues(
            self) -> AsyncGenerator[
                IGithubTrackedIssue,
                IGithubTrackedIssue]:
        """Iterate duplicate issues."""
        raise NotImplementedError

    @property  # type:ignore
    @abstracts.interfacemethod
    def github(self) -> IGithubAPI:
        """Github API."""
        raise NotImplementedError

    @property  # type:ignore
    @abstracts.interfacemethod
    def issue_author(self) -> str:
        """Issue author to search on for tracked issues."""
        raise NotImplementedError

    @property  # type:ignore
    @abstracts.interfacemethod
    def issue_class(self) -> Type[IGithubIssue]:
        """Issue class."""
        raise NotImplementedError

    @property  # type:ignore
    @abstracts.interfacemethod
    async def issues(self) -> dict[str, IGithubTrackedIssue]:
        """Dictionary of current tracked issues."""
        raise NotImplementedError

    @property  # type:ignore
    @abstracts.interfacemethod
    def issues_search_tpl(self):
        """String template for search query string."""
        raise NotImplementedError

    @property  # type:ignore
    @abstracts.interfacemethod
    def labels(self) -> tuple[str, ...]:
        """Labels to mark issues with."""
        raise NotImplementedError

    @property  # type:ignore
    @abstracts.interfacemethod
    async def missing_labels(self) -> tuple[str, ...]:
        """Missing Github issue labels."""
        raise NotImplementedError

    @property  # type:ignore
    @abstracts.interfacemethod
    async def open_issues(self) -> tuple[IGithubTrackedIssue, ...]:
        """All current open, matching issues."""
        raise NotImplementedError

    @property  # type:ignore
    @abstracts.interfacemethod
    def repo(self) -> IGithubRepo:
        """Github repo."""
        raise NotImplementedError

    @property  # type:ignore
    @abstracts.interfacemethod
    def repo_name(self) -> str:
        """Name of the repo to manage issues on."""
        raise NotImplementedError

    @property  # type:ignore
    @abstracts.interfacemethod
    def title_re(self) -> Pattern[str]:
        """Regex for matching/parsing issue titles."""
        raise NotImplementedError

    @property  # type:ignore
    @abstracts.interfacemethod
    def title_prefix(self) -> str:
        """Issue title prefix."""
        raise NotImplementedError

    @property  # type:ignore
    @abstracts.interfacemethod
    async def titles(self) -> tuple[str, ...]:
        """tuple of current matching issue titles."""
        raise NotImplementedError

    @abstracts.interfacemethod
    async def create(self, **kwargs) -> IGithubTrackedIssue:
        """Create a tracked issue."""
        raise NotImplementedError

    @abstracts.interfacemethod
    async def issue_body(self, **kwargs) -> str:
        """Issue body for given kwargs."""
        raise NotImplementedError

    @abstracts.interfacemethod
    async def issue_title(self, **kwargs) -> str:
        """Issue title for given kwargs."""
        raise NotImplementedError

    @abstracts.interfacemethod
    def iter_issues(self) -> IGithubIterator:
        """Issues search iterator."""
        raise NotImplementedError

    @abstracts.interfacemethod
    async def track_issue(
            self,
            issues: dict[str, IGithubTrackedIssue],
            issue: IGithubTrackedIssue) -> bool:
        """Determine whether to add a matched issue to the tracked issues."""
        raise NotImplementedError


class IGithubIssuesTracker(metaclass=abstracts.Interface):

    @abstracts.interfacemethod
    def __init__(
            self,
            github: "IGithubAPI") -> None:
        raise NotImplementedError

    @property  # type:ignore
    @abstracts.interfacemethod
    def tracked_issues(self) -> dict[str, IGithubTrackedIssues]:
        raise NotImplementedError

    @abstracts.interfacemethod
    def __getitem__(self, k) -> IGithubTrackedIssues:
        raise NotImplementedError
