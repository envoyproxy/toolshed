
from typing import (
    Dict, List, Optional, TypedDict)


# Package defined types

class BaseDependencyMetadataDict(TypedDict):
    release_date: str
    version: str


class DependencyMetadataDict(BaseDependencyMetadataDict, total=False):
    cpe: Optional[str]
    urls: List[str]


DependenciesDict = Dict[str, DependencyMetadataDict]
