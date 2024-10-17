
from __future__ import annotations

import pathlib
from typing import (
    AsyncGenerator, ItemsView, Iterator, KeysView,
    ValuesView)

import aiohttp
from google.protobuf import descriptor_pool as _descriptor_pool
from packaging import version as _version

import abstracts

from aio.api import github as _github
from aio.core import directory as _directory, event

from envoy.base.utils import typing


class IProtobufSet(metaclass=abstracts.Interface):

    @abstracts.interfacemethod
    def __init__(self, descriptor_path: str | pathlib.Path) -> None:
        raise NotImplementedError

    @property
    @abstracts.interfacemethod
    def descriptor_pool(self) -> _descriptor_pool.DescriptorPool:
        raise NotImplementedError


class IProtobufValidator(metaclass=abstracts.Interface):

    @abstracts.interfacemethod
    def __init__(self, descriptor_path: str | pathlib.Path) -> None:
        raise NotImplementedError

    @abstracts.interfacemethod
    def protobuf_set_class(self) -> type[IProtobufSet]:
        raise NotImplementedError

    @abstracts.interfacemethod
    def validate_fragment(self, fragment: str, type_name: str = "") -> None:
        raise NotImplementedError

    @abstracts.interfacemethod
    def validate_yaml(self, fragment: str, type_name: str = "") -> None:
        raise NotImplementedError


class IInventories(metaclass=abstracts.Interface):
    """Manage Sphinx project documentation inventories."""

    @abstracts.interfacemethod
    def __init__(self, project: IProject) -> None:
        raise NotImplementedError

    @abstracts.interfacemethod
    def __iter__(self) -> Iterator[_version.Version]:
        if False:
            yield
        raise NotImplementedError

    @abstracts.interfacemethod
    def __getitem__(self, k: _version.Version) -> pathlib.Path:
        raise NotImplementedError

    @property
    @abstracts.interfacemethod
    def inventories(self) -> typing.InventoryDict:
        """Mapping of `version` -> `path` for inventory files."""
        raise NotImplementedError

    @property
    @abstracts.interfacemethod
    def paths(self) -> Iterator[pathlib.Path]:
        """Inventory file paths."""
        raise NotImplementedError

    @property
    @abstracts.interfacemethod
    def versions(self) -> typing.VersionDict:
        """Mapping of `minor_version` -> `version` for inventories."""
        raise NotImplementedError

    @property
    @abstracts.interfacemethod
    def versions_path(self) -> pathlib.Path:
        """Path to the inventory versions file."""
        raise NotImplementedError

    @abstracts.interfacemethod
    def changes_for_commit(self, change: typing.ProjectChangeDict) -> set[str]:
        """Changes to add/commit for a given change dictionary."""
        raise NotImplementedError

    @abstracts.interfacemethod
    async def sync(self) -> typing.SyncResultDict:
        """Synchronize the latest available inventories."""
        raise NotImplementedError


class IChangelogEntry(metaclass=abstracts.Interface):
    """A changelog entry."""

    @abstracts.interfacemethod
    def __init__(self, section: str, entry: typing.ChangeDict) -> None:
        raise NotImplementedError

    @abstracts.interfacemethod
    def __gt__(self, other: IChangelogEntry) -> bool:
        raise NotImplementedError

    @abstracts.interfacemethod
    def __lt__(self, other: IChangelogEntry) -> bool:
        raise NotImplementedError

    @property
    @abstracts.interfacemethod
    def area(self) -> str:
        """Tag/area for this entry."""
        raise NotImplementedError

    @property
    @abstracts.interfacemethod
    def change(self) -> str:
        """Description of the change for this entry."""
        raise NotImplementedError


class IChangelog(metaclass=abstracts.Interface):
    """A changelog."""

    @abstracts.interfacemethod
    def __init__(
            self,
            version: _version.Version,
            path: pathlib.Path) -> None:
        raise NotImplementedError

    @property
    @abstracts.interfacemethod
    async def data(self) -> typing.ChangelogDict:
        """Changes grouped by change type."""
        raise NotImplementedError

    @property
    @abstracts.interfacemethod
    def entry_class(self) -> type[IChangelogEntry]:
        raise NotImplementedError

    @property
    @abstracts.interfacemethod
    def path(self) -> pathlib.Path:
        """Path to this changelog."""
        raise NotImplementedError

    @property
    @abstracts.interfacemethod
    async def release_date(self) -> str:
        """Datestamp of this changelog."""
        raise NotImplementedError

    @property
    @abstracts.interfacemethod
    def version(self) -> str:
        """Version of this changelog."""
        raise NotImplementedError

    @abstracts.interfacemethod
    async def entries(self, section: str) -> list[IChangelogEntry]:
        """Changelog entries."""
        raise NotImplementedError


class IChangelogs(metaclass=abstracts.Interface):
    """Manage project changelogs."""

    @abstracts.interfacemethod
    def __init__(self, project: IProject) -> None:
        raise NotImplementedError

    @abstracts.interfacemethod
    def __iter__(self) -> Iterator[_version.Version]:
        if False:
            yield
        raise NotImplementedError

    @abstracts.interfacemethod
    def __getitem__(self, k: _version.Version) -> IChangelog:
        raise NotImplementedError

    @property
    @abstracts.interfacemethod
    def changelog_class(self) -> type[IChangelog]:
        raise NotImplementedError

    @property
    @abstracts.interfacemethod
    def changelog_paths(self) -> typing.ChangelogPathsDict:
        """Mapping of changelog versions to changelog file paths."""
        raise NotImplementedError

    @property
    @abstracts.interfacemethod
    def changelogs(self) -> typing.ChangelogsDict:
        """Ordered mapping of changelog versions to changelog objects."""
        raise NotImplementedError

    @property
    @abstracts.interfacemethod
    def current(self) -> _version.Version:
        """The current (most recent or active) changelog."""
        raise NotImplementedError

    @property
    @abstracts.interfacemethod
    def date_format(self) -> str:
        """Changelog date format."""
        raise NotImplementedError

    @property
    @abstracts.interfacemethod
    def datestamp(self) -> str:
        """Formatted current UTC date."""
        raise NotImplementedError

    @property
    @abstracts.interfacemethod
    async def is_pending(self) -> bool:
        """Flag indicating whether the current changelog is set to
        `Pending`."""
        raise NotImplementedError

    @property
    @abstracts.interfacemethod
    def sections(self) -> typing.ChangelogSectionsDict:
        """Changelog groupings/sections."""
        raise NotImplementedError

    @abstracts.interfacemethod
    def changes_for_commit(self, change: typing.ProjectChangeDict) -> set[str]:
        """Changes to add/commit for a given change dictionary."""
        raise NotImplementedError

    @abstracts.interfacemethod
    def items(self) -> ItemsView[_version.Version, IChangelog]:
        """Items from `self.changelogs`."""
        raise NotImplementedError

    @abstracts.interfacemethod
    def keys(self) -> KeysView[_version.Version]:
        """Keys from `self.changelogs`."""
        raise NotImplementedError

    @abstracts.interfacemethod
    async def sync(self) -> None:
        """Synchronize the latest available changelogs."""
        raise NotImplementedError

    @abstracts.interfacemethod
    def values(self) -> ValuesView[IChangelog]:
        """Values from `self.changelogs`."""
        raise NotImplementedError

    @abstracts.interfacemethod
    def write_current(self) -> None:
        """Create the `current.yaml` changelog file from a template."""
        raise NotImplementedError

    @abstracts.interfacemethod
    def write_date(self) -> None:
        """Set the date in the `current.yaml` changelog file."""
        raise NotImplementedError

    @abstracts.interfacemethod
    def write_version(self, version: _version.Version) -> None:
        """Write the `current.yaml` file to the current version."""
        raise NotImplementedError


class IProject(event.IExecutive, metaclass=abstracts.Interface):

    def __init__(
            self,
            path: pathlib.Path | str = ".",
            version: _version.Version | None = None,
            github: _github.IGithubAPI | None = None,
            repo: _github.IGithubRepo | None = None,
            github_token: str | None = None,
            session: aiohttp.ClientSession | None = None) -> None:
        raise NotImplementedError

    @property
    @abstracts.interfacemethod
    def archived_versions(self) -> tuple[_version.Version, ...]:
        """Non/archived version logic."""
        raise NotImplementedError

    @property
    @abstracts.interfacemethod
    def changelogs(self) -> IChangelogs:
        """Project changelogs."""
        raise NotImplementedError

    @property
    @abstracts.interfacemethod
    def changelogs_class(self) -> type[IChangelogs]:
        raise NotImplementedError

    @property
    @abstracts.interfacemethod
    def dev_version(self) -> _version.Version | None:
        """Returns the current version iff its a dev version."""
        raise NotImplementedError

    @property
    @abstracts.interfacemethod
    def directory(self) -> _directory.ADirectory:
        """The project directory."""
        raise NotImplementedError

    @property
    @abstracts.interfacemethod
    def directory_class(self) -> type[_directory.ADirectory]:
        raise NotImplementedError

    @property
    @abstracts.interfacemethod
    def inventories(self) -> IInventories:
        """Project inventories."""
        raise NotImplementedError

    @property
    @abstracts.interfacemethod
    def inventories_class(self) -> type[IInventories]:
        raise NotImplementedError

    @property
    @abstracts.interfacemethod
    def is_dev(self) -> bool:
        """Flag indicating whether the project is in "dev" mode."""
        raise NotImplementedError

    @property
    @abstracts.interfacemethod
    def is_main_dev(self) -> bool:
        """If the patch version is `0` and its a dev branch then we are on
        `main`"""
        raise NotImplementedError

    @property
    @abstracts.interfacemethod
    async def json_data(self) -> str:
        """Changes grouped by change type."""
        raise NotImplementedError

    @property
    @abstracts.interfacemethod
    def minor_version(self) -> _version.Version:
        """Minor version for the current version."""
        raise NotImplementedError

    @property
    @abstracts.interfacemethod
    def minor_versions(self) -> typing.MinorVersionsDict:
        """Ordered mapping `minor_version` -> `patch_versions` for the
        project."""
        raise NotImplementedError

    @property
    @abstracts.interfacemethod
    def path(self) -> pathlib.Path:
        """Path to the project root."""
        raise NotImplementedError

    @property
    @abstracts.interfacemethod
    def rel_version_path(self) -> pathlib.Path:
        """Path to the project version file."""
        raise NotImplementedError

    @property
    @abstracts.interfacemethod
    def repo(self) -> _github.IGithubRepo:
        """Project github repo."""
        raise NotImplementedError

    @property
    @abstracts.interfacemethod
    def session(self) -> aiohttp.ClientSession:
        """HTTP client session used for retrieving project data."""
        raise NotImplementedError

    @property
    @abstracts.interfacemethod
    def stable_versions(self) -> tuple[_version.Version, ...]:
        """Currently supported stable versions."""
        raise NotImplementedError

    @property
    @abstracts.interfacemethod
    def version(self) -> _version.Version:
        """Current project version."""
        raise NotImplementedError

    @abstracts.interfacemethod
    async def commit(
            self,
            change: typing.ProjectChangeDict,
            msg: str) -> AsyncGenerator:
        """Commit a set of changes."""
        raise NotImplementedError

    @abstracts.interfacemethod
    async def dev(self) -> typing.ProjectDevResultDict:
        """Switch the project to "dev" mode."""
        raise NotImplementedError

    @abstracts.interfacemethod
    def is_current(self, version: _version.Version) -> bool:
        """Check if a version is the current one."""
        raise NotImplementedError

    @abstracts.interfacemethod
    async def publish(self) -> typing.ProjectPublishResultDict:
        """Publish a project release."""
        raise NotImplementedError

    @abstracts.interfacemethod
    async def release(self) -> typing.ProjectReleaseResultDict:
        """Switch the project to "release" mode."""
        raise NotImplementedError

    @abstracts.interfacemethod
    async def sync(self) -> typing.ProjectSyncResultDict:
        """Synchronize project resources."""
        raise NotImplementedError

    @abstracts.interfacemethod
    async def trigger(
            self,
            **kwargs) -> typing.ProjectTriggerResultDict:
        """Trigger a project workflow."""
        raise NotImplementedError
