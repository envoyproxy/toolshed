
from functools import cached_property
from typing import Dict, List, Optional, Type

import abstracts

from aio.api import github, nist

from envoy.dependency import check


@abstracts.implementer(check.ADependencyCVE)
class DependencyCVE:
    pass


@abstracts.implementer(check.ADependencyCVEs)
class DependencyCVEs:

    @property
    def cpe_class(self) -> Type[nist.ACPE]:
        return nist.CPE

    @property
    def cve_class(self) -> Type[check.ADependencyCVE]:
        return DependencyCVE

    @cached_property
    def ignored_cves(self) -> List[str]:
        return super().ignored_cves

    @property
    def nist_downloader_class(self) -> Type[nist.NISTDownloader]:
        return nist.NISTDownloader


@abstracts.implementer(check.ADependency)
class Dependency:

    @property
    def release_class(self) -> Type[check.ADependencyGithubRelease]:
        return DependencyGithubRelease


@abstracts.implementer(check.ADependencyGithubRelease)
class DependencyGithubRelease:
    pass


@abstracts.implementer(check.AGithubDependencyReleaseIssue)
class GithubDependencyReleaseIssue:
    pass


@abstracts.implementer(github.IGithubTrackedIssues)
class GithubDependencyReleaseIssues(check.AGithubDependencyReleaseIssues):

    @property
    def issue_class(self) -> Type[GithubDependencyReleaseIssue]:
        return GithubDependencyReleaseIssue


@abstracts.implementer(github.IGithubIssuesTracker)
class GithubDependencyIssuesTracker(github.AGithubIssuesTracker):

    @cached_property
    def tracked_issues(self) -> Dict:
        return dict(
            releases=GithubDependencyReleaseIssues(self.github))


@abstracts.implementer(check.ADependencyChecker)
class DependencyChecker:

    @property
    def access_token(self) -> Optional[str]:
        return super().access_token

    @property
    def cves_class(self) -> Type[check.ADependencyCVEs]:
        return DependencyCVEs

    @property
    def dependency_class(self) -> Type[check.ADependency]:
        return Dependency

    @cached_property
    def dependency_metadata(self) -> check.typing.DependenciesDict:
        return super().dependency_metadata

    @property
    def issues_class(self) -> Type[github.IGithubIssuesTracker]:
        return GithubDependencyIssuesTracker
