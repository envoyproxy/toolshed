

from typing import TypedDict


# Package defined types

class BaseDependencyMetadataDict(TypedDict):
    release_date: str
    version: str
    urls: list[str]
    sha256: str


class DependencyMetadataDict(BaseDependencyMetadataDict, total=False):
    cpe: str | None


DependenciesDict = dict[str, DependencyMetadataDict]
