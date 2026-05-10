
from functools import cached_property

import abstracts

from aio.api import github

from envoy.dependency import check


class Dependency(check.ADependency):

    @property
    def release_class(self) -> type[check.ADependencyGithubRelease]:
        return DependencyGithubRelease


class DependencyGithubRelease(check.ADependencyGithubRelease):
    pass


class GithubDependencyReleaseIssue(check.AGithubDependencyReleaseIssue):
    pass


@abstracts.implementer(github.IGithubTrackedIssues)
class GithubDependencyReleaseIssues(check.AGithubDependencyReleaseIssues):

    @property
    def issue_class(self) -> type[GithubDependencyReleaseIssue]:
        return GithubDependencyReleaseIssue


@abstracts.implementer(github.IGithubIssuesTracker)
class GithubDependencyIssuesTracker(github.AGithubIssuesTracker):

    @cached_property
    def tracked_issues(self) -> dict:
        return dict(
            releases=GithubDependencyReleaseIssues(self.github))


class DependencyChecker(check.ADependencyChecker):

    @property
    def access_token(self) -> str | None:
        return super().access_token

    @property
    def dependency_class(self) -> type[check.ADependency]:
        return Dependency

    @cached_property
    def dependency_metadata(self) -> check.typing.DependenciesDict:
        return super().dependency_metadata

    @property
    def issues_class(self) -> type[github.IGithubIssuesTracker]:
        return GithubDependencyIssuesTracker
