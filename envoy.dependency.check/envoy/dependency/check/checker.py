
import pathlib
import sys
from functools import cached_property
from typing import Type

import abstracts

from envoy.dependency import check


@abstracts.implementer(check.AGithubDependency)
class GithubDependency:

    @property
    def release_class(self):
        return DependencyGithubRelease


@abstracts.implementer(check.ADependencyGithubRelease)
class DependencyGithubRelease:
    pass


@abstracts.implementer(check.AGithubDependencyIssue)
class GithubDependencyIssue:
    pass


@abstracts.implementer(check.AGithubDependencyIssues)
class GithubDependencyIssues:

    @property
    def issue_class(self):
        return GithubDependencyIssue


@abstracts.implementer(check.ADependencyChecker)
class DependencyChecker:

    @cached_property
    def access_token(self):
        return super().access_token

    @cached_property
    def dependency_metadata(self):
        return super().dependency_metadata

    @property
    def github_dependency_class(self):
        return GithubDependency

    @property
    def issues_class(self):
        return GithubDependencyIssues


def main(*args) -> int:
    return DependencyChecker(*args)()


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:]))
