
import pathlib
from typing import (
    ItemsView, Iterator, KeysView, List,
    Optional, Tuple, Type, ValuesView)

from packaging import version as _version

import abstracts

from envoy.base.utils import typing


class IChangelogEntry(metaclass=abstracts.Interface):

    def __init__(self, section: str, entry: typing.ChangeDict) -> None:
        raise NotImplementedError

    @abstracts.interfacemethod
    def __gt__(self, other: "IChangelogEntry") -> bool:
        raise NotImplementedError

    @abstracts.interfacemethod
    def __lt__(self, other: "IChangelogEntry") -> bool:
        raise NotImplementedError

    @property  # type:ignore
    @abstracts.interfacemethod
    def area(self) -> str:
        raise NotImplementedError

    @property  # type:ignore
    @abstracts.interfacemethod
    def change(self) -> str:
        raise NotImplementedError


class IChangelog(metaclass=abstracts.Interface):

    def __init__(self, version: _version.Version, path: pathlib.Path) -> None:
        raise NotImplementedError

    @property  # type:ignore
    @abstracts.interfacemethod
    def data(self) -> typing.ChangelogDict:
        raise NotImplementedError

    @property  # type:ignore
    @abstracts.interfacemethod
    def entry_class(self) -> Type[IChangelogEntry]:
        raise NotImplementedError

    @property  # type:ignore
    @abstracts.interfacemethod
    def release_date(self) -> str:
        raise NotImplementedError

    @property  # type:ignore
    @abstracts.interfacemethod
    def version(self) -> str:
        raise NotImplementedError

    @abstracts.interfacemethod
    def entries(self, section: str) -> List[IChangelogEntry]:
        raise NotImplementedError


class IChangelogs(metaclass=abstracts.Interface):

    def __init__(self, project_version: _version.Version, path: str) -> None:
        raise NotImplementedError

    def __iter__(self) -> Iterator[_version.Version]:
        raise NotImplementedError

    def __getitem__(self, k: _version.Version) -> IChangelog:
        raise NotImplementedError

    @property  # type:ignore
    @abstracts.interfacemethod
    def changelog_class(self) -> Type[IChangelog]:
        raise NotImplementedError

    @property  # type:ignore
    @abstracts.interfacemethod
    def changelog_paths(self) -> typing.ChangelogPathsDict:
        raise NotImplementedError

    @property  # type:ignore
    @abstracts.interfacemethod
    def changelogs(self) -> typing.ChangelogsDict:
        raise NotImplementedError

    @property  # type:ignore
    @abstracts.interfacemethod
    def current(self) -> _version.Version:
        raise NotImplementedError

    @property  # type:ignore
    @abstracts.interfacemethod
    def sections(self) -> typing.ChangelogSectionsDict:
        raise NotImplementedError

    @abstracts.interfacemethod
    def items(self) -> ItemsView[_version.Version, IChangelog]:
        raise NotImplementedError

    @abstracts.interfacemethod
    def keys(self) -> KeysView[_version.Version]:
        raise NotImplementedError

    @abstracts.interfacemethod
    def values(self) -> ValuesView[IChangelog]:
        raise NotImplementedError


class IProject(metaclass=abstracts.Interface):

    def __init__(self, version: str) -> None:
        raise NotImplementedError

    @property  # type:ignore
    @abstracts.interfacemethod
    def archived_versions(self) -> Tuple[_version.Version, ...]:
        """Non/archived version logic."""
        raise NotImplementedError

    @property  # type:ignore
    @abstracts.interfacemethod
    def changelogs(self) -> IChangelogs:
        raise NotImplementedError

    @property  # type:ignore
    @abstracts.interfacemethod
    def changelogs_class(self) -> Type[IChangelogs]:
        raise NotImplementedError

    @property  # type:ignore
    @abstracts.interfacemethod
    def dev_version(self) -> Optional[_version.Version]:
        raise NotImplementedError

    @property  # type:ignore
    @abstracts.interfacemethod
    def is_dev(self) -> bool:
        raise NotImplementedError

    @property  # type:ignore
    @abstracts.interfacemethod
    def is_main_dev(self) -> bool:
        """If the patch version is `0` and its a dev branch then we are on
        `main`"""
        raise NotImplementedError

    @property  # type:ignore
    @abstracts.interfacemethod
    def minor_version(self) -> _version.Version:
        raise NotImplementedError

    @property  # type:ignore
    @abstracts.interfacemethod
    def minor_versions(self) -> typing.MinorVersionsDict:
        raise NotImplementedError

    @property  # type:ignore
    @abstracts.interfacemethod
    def stable_versions(self) -> Tuple[_version.Version, ...]:
        raise NotImplementedError

    @property  # type:ignore
    @abstracts.interfacemethod
    def version(self) -> _version.Version:
        raise NotImplementedError

    @abstracts.interfacemethod
    def is_current(self, version: _version.Version) -> bool:
        raise NotImplementedError
