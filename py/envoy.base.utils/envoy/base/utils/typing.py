
import pathlib
from typing import TypedDict

from packaging import version as _version

from envoy.base.utils import interface  # noqa: F401


class Change(str):

    def __add__(self, other: str) -> "Change":
        return Change(str(self) + other)


class SourceChangeDict(TypedDict):
    area: str
    change: str


class ChangeDict(TypedDict):
    area: str
    change: Change


ChangeList = list[ChangeDict]
SourceChangeList = list[SourceChangeDict]


class BaseChangelogDict(TypedDict):
    date: str


ChangelogChangeSectionsDict = dict[str, ChangeList]
SourceChangelogChangeSectionsDict = dict[str, SourceChangeList]


ChangelogSourceDict = dict[str, SourceChangeList | str | None]
ChangelogDict = dict[str, ChangeList | str]


ChangelogPathsDict = dict[_version.Version, pathlib.Path]
ChangelogsDict = dict[_version.Version, "interface.IChangelog"]
MinorVersionsDict = dict[_version.Version, tuple[_version.Version, ...]]


class BaseChangelogSectionDict(TypedDict):
    title: str


class ChangelogSectionDict(BaseChangelogSectionDict, total=False):
    description: str


ChangelogSectionsDict = dict[str, ChangelogSectionDict]


class ChangelogAreaDict(BaseChangelogSectionDict):
    pass


ChangelogAreasDict = dict[str, ChangelogAreaDict]


class ChangelogConfigDict(TypedDict, total=False):
    sections: ChangelogSectionsDict
    areas: ChangelogAreasDict


VersionConfigDict = dict[str, str]


class ProjectDevResultDict(TypedDict):
    date: str
    version: str
    old_version: _version.Version


SyncResultDict = dict[_version.Version, bool]


class ProjectReleaseResultDict(TypedDict):
    date: str
    version: str


class ProjectSyncResultDict(TypedDict):
    changelog: SyncResultDict
    inventory: SyncResultDict


class ProjectPublishResultDict(TypedDict):
    body: str
    commitish: str
    date: str
    tag_name: str
    url: str
    dry_run: str


class ProjectTriggerResultDict(TypedDict):
    workflow: str


class ProjectChangeDict(TypedDict, total=False):
    dev: ProjectDevResultDict
    publish: ProjectPublishResultDict
    release: ProjectReleaseResultDict
    sync: ProjectSyncResultDict
    trigger: ProjectTriggerResultDict


VersionDict = dict[_version.Version, _version.Version]
InventoryDict = dict[_version.Version, pathlib.Path]
