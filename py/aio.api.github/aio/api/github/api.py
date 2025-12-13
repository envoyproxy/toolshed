
import gidgethub.aiohttp

import abstracts

from .abstract import (
    AGithubActions,
    AGithubAPI,
    AGithubCommit,
    AGithubIssue,
    AGithubIssues,
    AGithubIterator,
    AGithubLabel,
    AGithubRelease,
    AGithubReleaseAssets,
    AGithubRepo,
    AGithubTag,
    AGithubWorkflows)
from . import interface


@abstracts.implementer(interface.IGithubActions)
class GithubActions(AGithubActions):
    pass


@abstracts.implementer(interface.IGithubWorkflows)
class GithubWorkflows(AGithubWorkflows):
    pass


@abstracts.implementer(interface.IGithubCommit)
class GithubCommit(AGithubCommit):
    pass


@abstracts.implementer(interface.IGithubIssue)
class GithubIssue(AGithubIssue):
    pass


@abstracts.implementer(interface.IGithubIssues)
class GithubIssues(AGithubIssues):
    pass


@abstracts.implementer(interface.IGithubIterator)
class GithubIterator(AGithubIterator):
    pass


@abstracts.implementer(interface.IGithubLabel)
class GithubLabel(AGithubLabel):
    pass


@abstracts.implementer(interface.IGithubRelease)
class GithubRelease(AGithubRelease):

    @property
    def assets_class(self) -> type[interface.IGithubReleaseAssets]:
        return GithubReleaseAssets


@abstracts.implementer(interface.IGithubReleaseAssets)
class GithubReleaseAssets(AGithubReleaseAssets):
    pass


@abstracts.implementer(interface.IGithubRepo)
class GithubRepo(AGithubRepo):
    pass


@abstracts.implementer(interface.IGithubTag)
class GithubTag(AGithubTag):
    pass


@abstracts.implementer(interface.IGithubAPI)
class GithubAPI(AGithubAPI):

    def __init__(self, session, *args, **kwargs) -> None:
        AGithubAPI.__init__(self, session, *args, **kwargs)

    @property
    def actions_class(self) -> type[AGithubActions]:
        return GithubActions

    @property
    def api_class(self) -> type[gidgethub.aiohttp.GitHubAPI]:
        return super().api_class

    @property
    def commit_class(self) -> type[AGithubCommit]:
        return GithubCommit

    @property
    def issue_class(self) -> type[AGithubIssue]:
        return GithubIssue

    @property
    def issues_class(self) -> type[AGithubIssues]:
        return GithubIssues

    @property
    def iterator_class(self) -> type[AGithubIterator]:
        return GithubIterator

    @property
    def label_class(self) -> type[AGithubLabel]:
        return GithubLabel

    @property
    def release_class(self) -> type[AGithubRelease]:
        return GithubRelease

    @property
    def repo_class(self) -> type[AGithubRepo]:
        return GithubRepo

    @property
    def tag_class(self) -> type[AGithubTag]:
        return GithubTag

    @property
    def workflows_class(self) -> type[AGithubWorkflows]:
        return GithubWorkflows
