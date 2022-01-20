
from functools import cached_property
from typing import List, Optional, Type

import abstracts

from envoy.dependency import check


@abstracts.implementer(check.ADependencyCPE)
class DependencyCPE:
    pass


@abstracts.implementer(check.ADependencyCVE)
class DependencyCVE:

    @property
    def cpe_class(self) -> Type[check.ADependencyCPE]:
        return DependencyCPE

    @property
    def version_matcher_class(
            self) -> Type[check.ADependencyCVEVersionMatcher]:
        return DependencyCVEVersionMatcher


@abstracts.implementer(check.ADependencyCVEVersionMatcher)
class DependencyCVEVersionMatcher:
    pass


@abstracts.implementer(check.ADependencyCVEs)
class DependencyCVEs:

    @property
    def cpe_class(self) -> Type[check.ADependencyCPE]:
        return DependencyCPE

    @property
    def cve_class(self) -> Type[check.ADependencyCVE]:
        return DependencyCVE

    @cached_property
    def ignored_cves(self) -> List[str]:
        return super().ignored_cves


@abstracts.implementer(check.ADependency)
class Dependency:

    @property
    def release_class(self) -> Type[check.ADependencyGithubRelease]:
        return DependencyGithubRelease


@abstracts.implementer(check.ADependencyGithubRelease)
class DependencyGithubRelease:
    pass


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
