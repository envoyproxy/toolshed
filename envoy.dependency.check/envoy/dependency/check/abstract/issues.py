
from functools import cached_property
from typing import Dict, Optional, Tuple

from packaging import version

import abstracts

from aio.api import github as _github


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
TITLE_PREFIX = "Newer release available"
TITLE_RE_TPL = r"{title_prefix} [`]?([\w\-\.]+)[`]?: ([\w\-\.]+)"
TITLE_TPL = (
    "{title_prefix} `{dep.id}`: {newer_release.tag_name} "
    "(current: {dep.github_version_name})")


@abstracts.implementer(_github.IGithubTrackedIssue)
class AGithubDependencyReleaseIssue(
        _github.AGithubTrackedIssue,
        metaclass=abstracts.Abstraction):
    """Github issue associated with a dependency."""

    @property
    def parse_vars(self) -> Tuple[str, ...]:
        return ("key", "version")

    @cached_property
    def version(self) -> Optional[version.Version]:
        """Parsed dependency version of an issue."""
        return (
            version.parse(self.parsed["version"])
            if "version" in self.parsed
            else None)

    async def close_old(
            self,
            old_issue: "AGithubDependencyReleaseIssue",
            **kwargs) -> None:
        # TODO: reassign any users old -> new issue
        newer_release = await kwargs["dep"].newer_release
        await old_issue.comment(
            self.closing_tpl.format(
                newer_release=newer_release,
                newer_release_date=await newer_release.date,
                full_name=kwargs["dep"].repo.name,
                repo_location=self.repo_name,
                number=self.number))
        await old_issue.close()


@abstracts.implementer(_github.IGithubTrackedIssues)
class AGithubDependencyReleaseIssues(
        _github.AGithubTrackedIssues,
        metaclass=abstracts.Abstraction):
    """Github issues associated with released dependencies."""

    @property
    def body_tpl(self) -> str:
        return BODY_TPL

    @property
    def closing_tpl(self) -> str:
        return CLOSING_TPL

    @property
    def issue_author(self) -> str:
        return super().issue_author

    @property
    def issues_search_tpl(self) -> str:
        return super().issues_search_tpl

    @property
    def labels(self) -> Tuple[str, ...]:
        return LABELS

    @property
    def repo_name(self) -> str:
        return GITHUB_REPO_LOCATION

    @property
    def title_prefix(self) -> str:
        return TITLE_PREFIX

    @property
    def title_re_tpl(self) -> str:
        return TITLE_RE_TPL

    @property
    def title_tpl(self) -> str:
        return TITLE_TPL

    async def issue_body(self, **kwargs) -> str:
        newer_release = await kwargs["dep"].newer_release
        return self.body_tpl.format(
            dep=kwargs["dep"],
            newer_release=newer_release,
            newer_release_date=await newer_release.date,
            release_date=await kwargs["dep"].release.date)

    async def issue_title(self, **kwargs) -> str:
        return self.title_tpl.format(
            dep=kwargs["dep"],
            title_prefix=self.title_prefix,
            newer_release=await kwargs["dep"].newer_release)

    def track_issue(  # type:ignore[override]
            self,
            issues: Dict[str, AGithubDependencyReleaseIssue],
            issue: AGithubDependencyReleaseIssue) -> bool:
        if issue.key not in issues:
            return True
        if not (existing_issue_version := issues[issue.key].version):
            return bool(issue.version)
        if not issue.version:
            return bool(existing_issue_version)
        return issue.version > existing_issue_version
