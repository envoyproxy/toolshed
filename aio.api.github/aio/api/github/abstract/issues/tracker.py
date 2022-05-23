
import abc
import re
from functools import cached_property
from typing import (
    Any, AsyncGenerator, Dict,
    Optional, Pattern, Tuple, Type)

import abstracts

from aio.api.github import exceptions, interface
from aio.core.functional import async_property


ISSUE_AUTHOR = "app/github-actions"
ISSUES_SEARCH_TPL = (
    "in:title {self.title_prefix} is:open "
    "is:issue author:{self.issue_author}")


@abstracts.implementer(interface.IGithubTrackedIssue)
class AGithubTrackedIssue(metaclass=abstracts.Abstraction):

    def __init__(
            self,
            issues: interface.IGithubTrackedIssues,
            issue: interface.IGithubIssue) -> None:
        self.issues = issues
        self.issue = issue

    @property
    def body(self) -> str:
        return self.issue.body

    @property
    def closing_tpl(self) -> str:
        return self.issues.closing_tpl

    @property
    def key(self) -> Optional[str]:
        return self.parsed.get("key")

    @property
    def number(self) -> int:
        return self.issue.number

    @property
    def parse_vars(self) -> Tuple[str, ...]:
        return ("key", )

    @cached_property
    def parsed(self) -> Dict[str, str]:
        parsed = self.title_re.search(self.title)
        return (
            {k: parsed.group(i + 1)
             for i, k
             in enumerate(self.parse_vars)}
            if parsed
            else {})

    @property
    def repo_name(self) -> str:
        return self.issues.repo_name

    @property
    def title(self) -> str:
        return self.issue.title

    @property
    def title_re(self) -> Pattern[str]:
        return self.issues.title_re

    async def close(self) -> interface.IGithubIssue:
        return await self.issue.close()

    async def close_duplicate(
            self,
            old_issue: interface.IGithubTrackedIssue) -> None:
        # TODO: add "closed as duplicate" comment
        await old_issue.close()

    async def comment(self, comment: str) -> Any:
        return await self.issue.comment(comment)


@abstracts.implementer(interface.IGithubTrackedIssues)
class AGithubTrackedIssues(metaclass=abstracts.Abstraction):

    def __init__(
            self,
            github: interface.IGithubAPI,
            issue_author: Optional[str] = None,
            repo_name: Optional[str] = None) -> None:
        self._github = github
        self._issue_author = issue_author
        self._repo_name = repo_name

    async def __aiter__(
            self) -> AsyncGenerator[
                interface.IGithubTrackedIssue,
                interface.IGithubIssue]:
        async for issue in self.iter_issues():
            if (issue := self.issue_class(self, issue)).key:
                yield issue

    @property  # type:ignore
    @abstracts.interfacemethod
    def closing_tpl(self) -> str:
        raise NotImplementedError

    @async_property
    async def duplicate_issues(
            self) -> AsyncGenerator[
                interface.IGithubTrackedIssue,
                interface.IGithubTrackedIssue]:
        issues = (await self.issues).values()
        for issue in await self.open_issues:
            if issue not in issues:
                yield issue

    @property
    def github(self) -> interface.IGithubAPI:
        return self._github

    @property
    @abc.abstractmethod
    def issue_author(self) -> str:
        return self._issue_author or ISSUE_AUTHOR

    @property  # type:ignore
    @abstracts.interfacemethod
    def issue_class(self) -> Type[interface.IGithubTrackedIssue]:
        raise NotImplementedError

    @async_property(cache=True)
    async def issues(self) -> Dict[str, interface.IGithubTrackedIssue]:
        issues: Dict[str, interface.IGithubTrackedIssue] = {}
        for issue in await self.open_issues:
            if self.track_issue(issues, issue):
                issues[issue.key] = issue
        return issues

    @property  # type:ignore
    @abc.abstractmethod
    def issues_search_tpl(self):
        return ISSUES_SEARCH_TPL

    @property  # type:ignore
    @abstracts.interfacemethod
    def labels(self) -> Tuple[str, ...]:
        raise NotImplementedError

    @async_property(cache=True)
    async def missing_labels(self) -> Tuple[str, ...]:
        found = []
        async for label in self.repo.labels:
            if label.name in self.labels:
                found.append(label.name)
            if len(found) == len(self.labels):
                break
        return tuple(
            label
            for label
            in self.labels
            if label not in found)

    @async_property(cache=True)
    async def open_issues(self) -> Tuple[interface.IGithubTrackedIssue, ...]:
        issues = []
        async for issue in self:
            issues.append(issue)
        return tuple(issues)

    @cached_property
    def repo(self) -> interface.IGithubRepo:
        return self.github[self.repo_name]

    @property  # type:ignore
    @abstracts.interfacemethod
    def repo_name(self) -> str:
        raise NotImplementedError

    @cached_property
    def title_re(self) -> Pattern[str]:
        return re.compile(
            self.title_re_tpl.format(
                title_prefix=self.title_prefix))

    @property  # type:ignore
    @abstracts.interfacemethod
    def title_prefix(self) -> str:
        raise NotImplementedError

    @property  # type:ignore
    @abstracts.interfacemethod
    def title_re_tpl(self):
        raise NotImplementedError

    @property  # type:ignore
    @abstracts.interfacemethod
    def title_tpl(self):
        raise NotImplementedError

    @async_property(cache=True)
    async def titles(self) -> Tuple[str, ...]:
        return tuple(issue.title for issue in await self.open_issues)

    async def create(
            self,
            **kwargs) -> interface.IGithubTrackedIssue:
        issue_title = await self.issue_title(**kwargs)
        if issue_title in await self.titles:
            raise exceptions.IssueExists(issue_title)
        return self.issue_class(
            self,
            await self.repo.issues.create(
                issue_title,
                body=await self.issue_body(**kwargs),
                labels=self.labels))

    async def issue_body(self, **kwargs) -> str:
        raise NotImplementedError

    async def issue_title(self, **kwargs) -> str:
        raise NotImplementedError

    def iter_issues(self) -> "interface.IGithubIterator":
        return self.repo.issues.search(
            self.issues_search_tpl.format(self=self))

    def track_issue(
            self,
            issues: Dict[str, interface.IGithubTrackedIssue],
            issue: interface.IGithubTrackedIssue) -> bool:
        return issue.key not in issues


@abstracts.implementer(interface.IGithubIssuesTracker)
class AGithubIssuesTracker(metaclass=abstracts.Abstraction):
    """Github issue tracker."""

    def __init__(self, github) -> None:
        self.github = github

    def __getitem__(self, k) -> interface.IGithubTrackedIssues:
        return self.tracked_issues[k]

    @property  # type:ignore
    @abstracts.interfacemethod
    def tracked_issues(self) -> Dict[str, interface.IGithubTrackedIssues]:
        raise NotImplementedError
