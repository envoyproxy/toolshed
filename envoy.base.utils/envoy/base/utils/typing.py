
import pathlib
from typing import Dict, List, Optional, Tuple, TypedDict

from packaging import version

from envoy.base.utils import interface


class ChangeDict(TypedDict):
    area: str
    change: str


ChangeList = List[ChangeDict]


class BaseChangelogDict(TypedDict):
    date: str


class ChangelogDict(BaseChangelogDict, total=False):
    # This should match envoy:changelogs/sections.yaml
    changes: Optional[ChangeList]
    behavior_changes: Optional[ChangeList]
    minor_behavior_changes: Optional[ChangeList]
    bug_fixes: Optional[ChangeList]
    removed_config_or_runtime: Optional[ChangeList]
    new_features: Optional[ChangeList]
    deprecated: Optional[ChangeList]


ChangelogPathsDict = Dict[version.Version, pathlib.Path]
ChangelogsDict = Dict[version.Version, "interface.IChangelog"]
MinorVersionsDict = Dict[version.Version, Tuple[version.Version, ...]]


class BaseChangelogSectionDict(TypedDict):
    title: str


class ChangelogSectionDict(BaseChangelogSectionDict, total=False):
    description: str


ChangelogSectionsDict = Dict[str, ChangelogSectionDict]
