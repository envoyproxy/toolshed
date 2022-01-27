"""Abstract dependency."""

from functools import cached_property
from typing import List, Optional, Set, Type

from packaging import version

import abstracts

from aio.api import github
from aio.core.functional import async_property

from envoy.dependency.check import abstract, exceptions, typing


class ADependency(metaclass=abstracts.Abstraction):
    """Github dependency."""

    def __init__(
            self,
            id: str,
            metadata: "typing.DependencyMetadataDict",
            github: github.AGithubAPI) -> None:
        self.id = id
        self.metadata = metadata
        self.github = github

    def __gt__(self, other: "ADependency") -> bool:
        return self.id > other.id

    def __lt__(self, other: "ADependency") -> bool:
        return self.id < other.id

    def __str__(self):
        return f"{self.id}@{self.version}"

    @async_property(cache=True)
    async def commits_since_current(self) -> int:
        """Commits since current commit/tag."""
        count = await self.repo.commits(
            since=await self.release.timestamp_commit).total_count
        return count and count - 1 or count

    @cached_property
    def cpe(self) -> Optional[str]:
        """Configured CPE for this dependency."""
        return (
            str(self.metadata["cpe"])
            if self.metadata.get("cpe", "N/A") != "N/A"
            else None)

    @property
    def github_filetypes(self) -> Set[str]:
        return {".tar.gz", ".zip"}

    @cached_property
    def github_url(self) -> Optional[str]:
        """Github URL."""
        for url in self.urls:
            if url.startswith('https://github.com/'):
                return url

    @cached_property
    def github_version(self) -> str:
        """Github version, as parsed from the URL."""
        if self.url_components[5] != 'archive':
            # Release tag is a path component.
            if self.url_components[5] != 'releases':
                raise exceptions.BadGithubURL(
                    "Unable to parse github URL components: "
                    f"{self.url_components[3:]}")
            return self.url_components[7]
        # Only support .tar.gz, .zip today. Figure out the release tag
        # from this filename.
        for filetype in self.github_filetypes:
            if self.url_components[-1].endswith(filetype):
                return self.url_components[-1][:-len(filetype)]
        raise exceptions.BadGithubURL(
            "Unrecognized Github release asset: "
            f"{self.url_components[3:]}")

    @property
    def github_version_name(self) -> str:
        """Github version, truncated to 7 char if its sha_hash."""
        return (
            self.github_version[0:7]
            if not self.release.tagged
            else self.github_version)

    @async_property
    async def has_recent_commits(self) -> bool:
        """Flag indicating whether there are more recent commits than the
        current pinned commit."""
        return await self.recent_commits > 1

    @async_property(cache=True)
    async def newer_release(
            self) -> Optional["abstract.ADependencyGithubRelease"]:
        """Release with highest semantic version if newer than the current
        release, or where pin is to tag or commit."""
        # TODO: consider adding `newer_tags` for deps that only create
        #   tags and not releases (eg tclap)
        newer_release = await self.repo.highest_release(
            since=await self.release.timestamp)
        return (
            self.release_class(
                self.repo,
                newer_release.tag_name,
                release=newer_release)
            if (newer_release
                and (version.parse(newer_release.tag_name)
                     != self.release.version))
            else None)

    @property
    def organization(self) -> str:
        """Github organization name."""
        return self.url_components[3]

    @property
    def project(self) -> str:
        """Github project name."""
        return self.url_components[4]

    @async_property(cache=True)
    async def recent_commits(self) -> int:
        """Count of commits since current pinned commit."""
        return (
            await self.commits_since_current
            if not self.release.tagged
            else 0)

    @cached_property
    def release(self) -> "abstract.ADependencyGithubRelease":
        """Github release."""
        return self.release_class(self.repo, self.github_version)

    @property  # type:ignore
    @abstracts.interfacemethod
    def release_class(self) -> Type["abstract.ADependencyGithubRelease"]:
        """Github release class."""
        raise NotImplementedError

    @property
    def release_date(self) -> str:
        """Release (or published) date of this dependency."""
        return self.metadata["release_date"]

    @async_property
    async def release_date_mismatch(self) -> bool:
        """Flag indicating the metadata date doesnt match the Github date."""
        return (
            self.release_date
            != await self.release.date)

    @cached_property
    def release_version(self) -> Optional[version.Version]:
        """Semantic version for the release of this dependency if available."""
        try:
            return version.Version(self.version)
        except version.InvalidVersion:
            return None

    @cached_property
    def repo(self) -> github.AGithubRepo:
        """Github repo for this dependency."""
        return self.github[f"{self.organization}/{self.project}"]

    @cached_property
    def url_components(self) -> List[str]:
        """Github URL components."""
        if not self.github_url:
            urls = "\n".join(self.urls)
            raise exceptions.NotGithubDependency(
                f'{self.id} is not a GitHub repository\n{urls}')
        # TODO: add/use a proper `GithubURLParser`
        return self.github_url.split('/')

    @property
    def urls(self) -> List[str]:
        """Urls of this dependency."""
        return self.metadata["urls"]

    @property
    def version(self) -> str:
        """Version string of this dependency."""
        return self.metadata["version"]
