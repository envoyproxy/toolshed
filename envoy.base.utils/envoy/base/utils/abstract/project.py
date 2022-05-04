import pathlib
from functools import cached_property
from typing import (
    ItemsView, Iterator, KeysView,
    List, Optional, Tuple, Type, ValuesView)

from packaging import version as _version
import yaml

import abstracts

from envoy.base import utils
from envoy.base.utils import exceptions, interface, typing


CHANGELOG_PATH_GLOB = "changelogs/*.*.*.yaml"
CHANGELOG_CURRENT_PATH = "changelogs/current.yaml"
CHANGELOG_SECTIONS_PATH = "changelogs/sections.yaml"


@abstracts.implementer(interface.IChangelogEntry)
class AChangelogEntry(metaclass=abstracts.Abstraction):

    def __init__(self, section: str, entry: typing.ChangeDict) -> None:
        self.section = section
        self.entry = entry

    def __gt__(self, other: interface.IChangelogEntry) -> bool:
        if self.area > other.area:
            return True
        if self.change > other.change:
            return True
        return False

    def __lt__(self, other: interface.IChangelogEntry) -> bool:
        return not self.__gt__(other)

    @property
    def area(self) -> str:
        return self.entry["area"]

    @property
    def change(self) -> str:
        return self.entry["change"]


@abstracts.implementer(interface.IChangelog)
class AChangelog(metaclass=abstracts.Abstraction):

    def __init__(self, version: _version.Version, path: pathlib.Path) -> None:
        self._version = version
        self.path = path

    @cached_property
    def data(self) -> typing.ChangelogDict:
        try:
            return utils.from_yaml(self.path, typing.ChangelogDict)
        except (yaml.reader.ReaderError, utils.TypeCastingError) as e:
            raise exceptions.ChangelogError(
                f"Failed to parse changelog ({self.path}): {e}")

    @property  # type:ignore
    @abstracts.interfacemethod
    def entry_class(self) -> Type[interface.IChangelogEntry]:
        raise NotImplementedError

    @property
    def release_date(self) -> str:
        return self.data["date"]

    @property
    def version(self) -> str:
        return self._version.base_version

    def entries(self, section: str) -> List[interface.IChangelogEntry]:
        return sorted(
            self.entry_class(section, entry)
            for entry
            in self.data[section])  # type:ignore


@abstracts.implementer(interface.IChangelogs)
class AChangelogs(metaclass=abstracts.Abstraction):

    def __init__(self, project_version: _version.Version, path: str) -> None:
        self.project_version = project_version
        self._path = path

    def __iter__(self) -> Iterator[_version.Version]:
        for k in self.changelogs:
            yield k

    def __getitem__(self, k: _version.Version) -> interface.IChangelog:
        return self.changelogs.__getitem__(k)

    @property  # type:ignore
    @abstracts.interfacemethod
    def changelog_class(self) -> Type[interface.IChangelog]:
        raise NotImplementedError

    @cached_property
    def changelog_paths(self) -> typing.ChangelogPathsDict:
        return {
            self._version_from_path(path): path
            for path
            in self.paths}

    @cached_property
    def changelogs(self) -> typing.ChangelogsDict:
        return {
            k: self.changelog_class(k, self.changelog_paths[k])
            for k
            in reversed(sorted(self.changelog_paths.keys()))}

    @cached_property
    def current(self) -> _version.Version:
        return next(iter(self.changelogs))

    @cached_property
    def path(self) -> pathlib.Path:
        return pathlib.Path(self._path)

    @property
    def paths(self) -> Tuple[pathlib.Path, ...]:
        return (
            *self.path.glob(CHANGELOG_PATH_GLOB),
            self.path.joinpath(CHANGELOG_CURRENT_PATH))

    @cached_property
    def sections(self) -> typing.ChangelogSectionsDict:
        try:
            return utils.from_yaml(
                self.sections_path,
                typing.ChangelogSectionsDict)
        except (yaml.reader.ReaderError, utils.TypeCastingError) as e:
            raise exceptions.ChangelogError(
                "Failed to parse changelog sections "
                f"({self.sections_path}): {e}")

    @property
    def sections_path(self) -> pathlib.Path:
        return self.path.joinpath(CHANGELOG_SECTIONS_PATH)

    def items(self) -> ItemsView[_version.Version, interface.IChangelog]:
        return self.changelogs.items()

    def keys(self) -> KeysView[_version.Version]:
        return self.changelogs.keys()

    def values(self) -> ValuesView[interface.IChangelog]:
        return self.changelogs.values()

    def _version_from_path(self, path: pathlib.Path) -> _version.Version:
        return _version.Version(
            path.stem
            if path.stem != "current"
            else self.project_version.base_version)


@abstracts.implementer(interface.IProject)
class AProject(metaclass=abstracts.Abstraction):

    def __init__(self, version: str, path: str = ".") -> None:
        self._version = version
        self._path = path

    @cached_property
    def archived_versions(self) -> Tuple[_version.Version, ...]:
        non_archive = (5 if self.is_main_dev else 4)
        return tuple(
            reversed(
                sorted(self.minor_versions.keys())))[non_archive:]

    @cached_property
    def changelogs(self) -> interface.IChangelogs:
        return self.changelogs_class(self.version, self._path)

    @property  # type:ignore
    @abstracts.interfacemethod
    def changelogs_class(self) -> Type[interface.IChangelogs]:
        raise NotImplementedError

    @cached_property
    def dev_version(self) -> Optional[_version.Version]:
        return self.changelogs.current if self.is_dev else None

    @property
    def is_dev(self) -> bool:
        return self.version.is_devrelease

    @property
    def is_main_dev(self) -> bool:
        return self.is_dev and self.version.micro == 0

    @cached_property
    def minor_version(self) -> _version.Version:
        return utils.minor_version_for(self.version)

    @cached_property
    def minor_versions(self) -> typing.MinorVersionsDict:
        minor_versions: dict = {}
        for changelog_version in self.changelogs:
            minor_version = utils.minor_version_for(changelog_version)
            minor_versions[minor_version] = minor_versions.get(
                minor_version, [])
            minor_versions[minor_version].append(changelog_version)
        return {
            k: self._patch_versions(v)
            for k, v
            in minor_versions.items()}

    @cached_property
    def stable_versions(self) -> Tuple[_version.Version, ...]:
        exclude = set(self.archived_versions)
        if self.is_main_dev:
            exclude.add(self.minor_version)
        return tuple(
            reversed(
                sorted(set(self.minor_versions.keys()) - exclude)))

    @cached_property
    def version(self) -> _version.Version:
        return _version.Version(self._version)

    def is_current(self, version: _version.Version) -> bool:
        return (
            self.version.base_version
            == version.base_version)

    def _patch_versions(
            self,
            versions: List[_version.Version]) -> Tuple[_version.Version, ...]:
        return tuple(
            reversed(
                sorted(
                    versions
                    if not self.is_dev
                    else (
                        v for v
                        in versions
                        if not self.is_current(v)))))
