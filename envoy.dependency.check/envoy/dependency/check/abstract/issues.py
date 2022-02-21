
import re
from functools import cached_property
from typing import (
    Any, AsyncGenerator, Dict, Optional, Pattern, Tuple, Type, Union)

from packaging import version

import abstracts

from aio.api import github
from aio.core.functional import async_property

from envoy.dependency.check import abstract


GITHUB_REPO_LOCATION = "envoyproxy/envoy"
LABELS = ("dependencies", "area/build", "no stalebot")
BODY_TPL = """
Package Name: {dep}
Current Version: {dep.github_version_name}@{release_date}
Available Version: {newer_release.tag_name}@{newer_release_date}
Upstream releases: https://github.com/{dep.release.repo.name}/releases
"""
CLOSING_TPL = """
New version is available for this package
New Version: {newer_release.tag_name}@{newer_release_date}
Upstream releases: https://github.com/{full_name}/releases
New Issue Link: https://github.com/{repo_location}/issues/{number}
"""
ISSUES_SEARCH_TPL = "in:title {self.title_prefix} is:open " + \
                    "is:issue author:github-actions[bot]"
TITLE_PREFIX = "Newer release available"
TITLE_RE_TPL = r"{title_prefix} [`]?([\w\-\.]+)[`]?: ([\w\-\.]+)"
TITLE_TPL = (
    "{title_prefix} `{dep.id}`: {newer_release.tag_name} "
    "(current: {dep.github_version_name})")


class AGithubDependencyIssue(metaclass=abstracts.Abstraction):
    """Github issue associated with a dependency."""

    def __init__(
            self,
            issues: "abstract.AGithubDependencyIssues",
            issue: github.AGithubIssue) -> None:
        self.issues = issues
        self.issue = issue

    @property
    def body(self) -> str:
        """Github issue body."""
        return self.issue.body

    @property
    def closing_tpl(self) -> str:
        """String template for closing comment."""
        return self.issues.closing_tpl

    @property
    def dep(self) -> Optional[str]:
        """Associated dependency id."""
        return self.parsed.get("dep")

    @property
    def number(self) -> int:
        """Github issue number."""
        return self.issue.number

    @cached_property
    def parsed(self) -> Dict[str, str]:
        """Parsed element from issue title."""
        parsed = self.title_re.search(self.title)
        return (
            dict(dep=parsed.group(1),
                 version=parsed.group(2))
            if parsed
            else {})

    @property
    def repo_name(self) -> str:
        """Github repo name."""
        return self.issues.repo_name

    @property
    def title(self) -> str:
        """Github issue title."""
        return self.issue.title

    @property
    def title_re(self) -> Pattern[str]:
        return self.issues.title_re

    @cached_property
    def version(self) -> Optional[
            Union[
                version.LegacyVersion,
                version.Version]]:
        """Version parsed from the title."""
        return (
            version.parse(self.parsed["version"])
            if "version" in self.parsed
            else None)

    async def close(self) -> github.AGithubIssue:
        """Close this issue."""
        return await self.issue.close()

    async def close_duplicate(
            self,
            old_issue: "AGithubDependencyIssue") -> None:
        """Close a duplicate issue of this one."""
        # TODO: add "closed as duplicate" comment
        await old_issue.close()

    async def close_old(
            self,
            old_issue: "AGithubDependencyIssue",
            dep: "abstract.ADependency") -> None:
        """Close old associated issue."""
        # TODO: reassign any users old -> new issue
        newer_release = await dep.newer_release
        await old_issue.comment(
            self.closing_tpl.format(
                newer_release=newer_release,
                newer_release_date=await newer_release.date,
                full_name=dep.repo.name,
                repo_location=self.repo_name,
                number=self.number))
        await old_issue.close()

    async def comment(self, comment: str) -> Any:
        """Comment on this issue."""
        return await self.issue.comment(comment)


class AGithubDependencyIssues(metaclass=abstracts.Abstraction):
    """Github issues associated with dependencies."""

    def __init__(
            self,
            github,
            body_tpl: str = BODY_TPL,
            closing_tpl: str = CLOSING_TPL,
            issues_search_tpl: str = ISSUES_SEARCH_TPL,
            labels: Tuple[str, ...] = LABELS,
            repo_name: str = GITHUB_REPO_LOCATION,
            title_prefix: str = TITLE_PREFIX,
            title_re_tpl: str = TITLE_RE_TPL,
            title_tpl: str = TITLE_TPL) -> None:
        self.github = github
        self.body_tpl = body_tpl
        self.closing_tpl = closing_tpl
        self.issues_search_tpl = issues_search_tpl
        self.labels = labels
        self.repo_name = repo_name
        self.title_prefix = title_prefix
        self.title_re_tpl = title_re_tpl
        self.title_tpl = title_tpl

    async def __aiter__(
            self) -> AsyncGenerator[
                AGithubDependencyIssue,
                github.GithubIssue]:
        async for issue in self.iter_issues():
            issue = self.issue_class(self, issue)
            if issue.dep:
                yield issue

    @async_property(cache=True)
    async def dep_issues(self) -> Dict[str, AGithubDependencyIssue]:
        """Dependency dictionary of current issues."""
        issues: Dict[str, AGithubDependencyIssue] = {}
        for issue in await self.open_issues:
            if issue.dep in issues:
                if issue.version <= issues[issue.dep].version:
                    continue
            issues[issue.dep] = issue
        return issues

    @async_property
    async def duplicate_issues(
            self) -> AsyncGenerator[
                AGithubDependencyIssue,
                AGithubDependencyIssue]:
        """Iterate duplicate issues."""
        dep_issues = await self.dep_issues
        for issue in await self.open_issues:
            if issue not in dep_issues.values():
                yield issue

    @property  # type:ignore
    @abstracts.interfacemethod
    def issue_class(self) -> Type[AGithubDependencyIssue]:
        """Issue class."""
        raise NotImplementedError

    @async_property(cache=True)
    async def missing_labels(self) -> Tuple[str, ...]:
        """Missing Github issue labels."""
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
    async def open_issues(self) -> Tuple[AGithubDependencyIssue, ...]:
        """All current open, matching issues."""
        issues = []
        async for issue in self:
            issues.append(issue)
        return tuple(issues)

    @cached_property
    def repo(self) -> github.AGithubRepo:
        """Github repo."""
        return self.github[self.repo_name]

    @cached_property
    def title_re(self) -> Pattern[str]:
        """Regex for matching/parsing issue titles."""
        return re.compile(
            self.title_re_tpl.format(
                title_prefix=self.title_prefix))

    @async_property(cache=True)
    async def titles(self) -> Tuple[str, ...]:
        """Tuple of current issue titles."""
        return tuple(issue.title for issue in await self.open_issues)

    async def create(
            self,
            dep: "abstract.ADependency") -> AGithubDependencyIssue:
        """Create an issue for a dependency."""
        issue_title = await self.issue_title(dep)
        if issue_title in await self.titles:
            raise github.exceptions.IssueExists(issue_title)
        return self.issue_class(
            self,
            await self.repo.issues.create(
                issue_title,
                body=await self.issue_body(dep),
                labels=self.labels))

    async def issue_body(self, dep: "abstract.ADependency") -> str:
        """Issue body for a dependency."""
        newer_release = await dep.newer_release
        return self.body_tpl.format(
            dep=dep,
            newer_release=newer_release,
            newer_release_date=await newer_release.date,
            release_date=await dep.release.date)

    async def issue_title(self, dep: "abstract.ADependency") -> str:
        """Issue title for a dependency."""
        return self.title_tpl.format(
            dep=dep,
            title_prefix=self.title_prefix,
            newer_release=await dep.newer_release)

    def iter_issues(self) -> github.AGithubIterator:
        """Issues search iterator."""
        return self.repo.issues.search(
            self.issues_search_tpl.format(self=self))
