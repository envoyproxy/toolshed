
from functools import cached_property

import abstracts

from aio.api import github

from envoy.dependency import check


NO_ISSUE_DEPENDENCIES = r"com_google_protobuf_protoc_[a-zA-Z0-9_]+$"
GITHUB_REPO_LOCATION = "envoyproxy/envoy"
LABELS = ("dependencies", "area/build", "no stalebot")


class Dependency(check.ADependency):
    """Envoy-specific dependency."""

    @property
    def release_class(self) -> type[check.ADependencyGithubRelease]:
        return DependencyGithubRelease


class DependencyGithubRelease(check.ADependencyGithubRelease):
    """Envoy-specific dependency release."""

    pass


class GithubDependencyReleaseIssue(check.AGithubDependencyReleaseIssue):
    """Envoy-specific dependency release issue."""

    pass


@abstracts.implementer(github.IGithubTrackedIssues)
class GithubDependencyReleaseIssues(check.AGithubDependencyReleaseIssues):
    """Envoy-specific dependency release issue tracker."""

    @property
    def issue_class(self) -> type[GithubDependencyReleaseIssue]:
        return GithubDependencyReleaseIssue

    @property
    def labels(self) -> tuple[str, ...]:
        return LABELS

    @property
    def repo_name(self) -> str:
        return GITHUB_REPO_LOCATION


@abstracts.implementer(github.IGithubIssuesTracker)
class GithubDependencyIssuesTracker(github.AGithubIssuesTracker):
    """Envoy-specific dependency issues tracker."""

    @cached_property
    def tracked_issues(self) -> dict[str, GithubDependencyReleaseIssues]:
        return dict(
            releases=GithubDependencyReleaseIssues(self.github))


class DependencyChecker(check.ADependencyChecker):
    """Envoy-specific dependency checker."""

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

    @property
    def no_dep_issues_re(self) -> str:
        return NO_ISSUE_DEPENDENCIES
