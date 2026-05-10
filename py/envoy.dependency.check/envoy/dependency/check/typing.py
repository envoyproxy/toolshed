

from typing import TypedDict


# Package defined types

class BaseDependencyMetadataDict(TypedDict):
    release_date: str
    version: str


class DependencyMetadataDict(BaseDependencyMetadataDict, total=False):
    cpe: str | None
    urls: list[str]
    sha256: str


DependenciesDict = dict[str, DependencyMetadataDict]
