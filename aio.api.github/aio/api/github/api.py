
from typing import Type

import gidgethub.aiohttp

import abstracts

from .abstract import (
    AGithubAPI,
    AGithubCommit,
    AGithubIssue,
    AGithubIssues,
    AGithubIterator,
    AGithubLabel,
    AGithubRelease,
    AGithubReleaseAssets,
    AGithubRepo,
    AGithubTag)
from . import interface


@abstracts.implementer(AGithubCommit)
class GithubCommit:
    pass


@abstracts.implementer(AGithubIssue)
class GithubIssue:
    pass


@abstracts.implementer(AGithubIssues)
class GithubIssues:
    pass


@abstracts.implementer(AGithubIterator)
class GithubIterator:
    pass


@abstracts.implementer(AGithubLabel)
class GithubLabel:
    pass


@abstracts.implementer(AGithubRelease)
class GithubRelease:

    @property
    def assets_class(self) -> Type["interface.IGithubReleaseAssets"]:
        return GithubReleaseAssets


@abstracts.implementer(AGithubReleaseAssets)
class GithubReleaseAssets:
    pass


@abstracts.implementer(AGithubRepo)
class GithubRepo:
    pass


@abstracts.implementer(AGithubTag)
class GithubTag:
    pass


@abstracts.implementer(AGithubAPI)
class GithubAPI:

    def __init__(self, session, *args, **kwargs) -> None:
        AGithubAPI.__init__(self, session, *args, **kwargs)

    @property
    def api_class(self) -> Type[gidgethub.aiohttp.GitHubAPI]:
        return super().api_class

    @property
    def commit_class(self) -> Type[AGithubCommit]:
        return GithubCommit

    @property
    def issue_class(self) -> Type[AGithubIssue]:
        return GithubIssue

    @property
    def issues_class(self) -> Type[AGithubIssues]:
        return GithubIssues

    @property
    def iterator_class(self) -> Type[AGithubIterator]:
        return GithubIterator

    @property
    def label_class(self) -> Type[AGithubLabel]:
        return GithubLabel

    @property
    def release_class(self) -> Type[AGithubRelease]:
        return GithubRelease

    @property
    def repo_class(self) -> Type[AGithubRepo]:
        return GithubRepo

    @property
    def tag_class(self) -> Type[AGithubTag]:
        return GithubTag
