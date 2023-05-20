
import pathlib
from typing import Dict, List, Optional, Tuple, TypedDict

from packaging import version as _version

from envoy.base.utils import interface


class Change(str):

    def __add__(self, other) -> "Change":
        return Change(str(self) + str(other))


class SourceChangeDict(TypedDict):
    area: str
    change: str


class ChangeDict(TypedDict):
    area: str
    change: Change


ChangeList = List[ChangeDict]
SourceChangeList = List[SourceChangeDict]


class BaseChangelogDict(TypedDict):
    date: str


class ChangelogSourceDict(BaseChangelogDict, total=False):
    # This should match envoy:changelogs/sections.yaml
    changes: Optional[SourceChangeList]
    behavior_changes: Optional[SourceChangeList]
    minor_behavior_changes: Optional[SourceChangeList]
    bug_fixes: Optional[SourceChangeList]
    removed_config_or_runtime: Optional[SourceChangeList]
    new_features: Optional[SourceChangeList]
    deprecated: Optional[SourceChangeList]


class ChangelogChangeSectionsDict(TypedDict, total=False):
    # This should match envoy:changelogs/sections.yaml
    changes: Optional[ChangeList]
    behavior_changes: Optional[ChangeList]
    minor_behavior_changes: Optional[ChangeList]
    bug_fixes: Optional[ChangeList]
    removed_config_or_runtime: Optional[ChangeList]
    new_features: Optional[ChangeList]
    deprecated: Optional[ChangeList]


class ChangelogDict(BaseChangelogDict, ChangelogChangeSectionsDict):
    pass


ChangelogPathsDict = Dict[_version.Version, pathlib.Path]
ChangelogsDict = Dict[_version.Version, "interface.IChangelog"]
MinorVersionsDict = Dict[_version.Version, Tuple[_version.Version, ...]]


class BaseChangelogSectionDict(TypedDict):
    title: str


class ChangelogSectionDict(BaseChangelogSectionDict, total=False):
    description: str


ChangelogSectionsDict = Dict[str, ChangelogSectionDict]

VersionConfigDict = Dict[str, str]


ProjectDevResultDict = Dict
SyncResultDict = Dict[_version.Version, bool]


class ProjectReleaseResultDict(TypedDict):
    date: str
    version: str


class ProjectSyncResultDict(TypedDict):
    changelog: SyncResultDict
    inventory: SyncResultDict


class ProjectPublishResultDict(TypedDict):
    commitish: str
    date: str
    tag_name: str
    url: str
    dry_run: str


class ProjectChangeDict(TypedDict, total=False):
    dev: ProjectDevResultDict
    publish: ProjectPublishResultDict
    release: ProjectReleaseResultDict
    sync: ProjectSyncResultDict


VersionDict = Dict[_version.Version, _version.Version]
InventoryDict = Dict[_version.Version, pathlib.Path]
