
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


class ChangelogSourceDict(BaseChangelogDict, total=False):
    # This should match envoy:changelogs/sections.yaml
    changes: SourceChangeList | None
    behavior_changes: SourceChangeList | None
    minor_behavior_changes: SourceChangeList | None
    bug_fixes: SourceChangeList | None
    removed_config_or_runtime: SourceChangeList | None
    new_features: SourceChangeList | None
    deprecated: SourceChangeList | None


class ChangelogChangeSectionsDict(TypedDict, total=False):
    # This should match envoy:changelogs/sections.yaml
    changes: ChangeList | None
    behavior_changes: ChangeList | None
    minor_behavior_changes: ChangeList | None
    bug_fixes: ChangeList | None
    removed_config_or_runtime: ChangeList | None
    new_features: ChangeList | None
    deprecated: ChangeList | None


class ChangelogDict(BaseChangelogDict, ChangelogChangeSectionsDict):
    pass


ChangelogPathsDict = dict[_version.Version, pathlib.Path]
ChangelogsDict = dict[_version.Version, "interface.IChangelog"]
MinorVersionsDict = dict[_version.Version, tuple[_version.Version, ...]]


class BaseChangelogSectionDict(TypedDict):
    title: str


class ChangelogSectionDict(BaseChangelogSectionDict, total=False):
    description: str


ChangelogSectionsDict = dict[str, ChangelogSectionDict]

VersionConfigDict = dict[str, str]


ProjectDevResultDict = dict
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
