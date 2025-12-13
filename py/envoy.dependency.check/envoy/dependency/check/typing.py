

from typing import Dict, List, Optional, TypedDict

from aio.api import nist


# Scanner configuration

class CVEConfigDict(TypedDict, total=False):
    ignored_cves: List[str]
    nist_url: str
    start_year: int


class DependencyCVEItemDict(nist.typing.CVEItemDict, total=False):
    score: str
    description: str
    last_modified_date: str
    published_date: str
    cpes: nist.typing.CPEsTuple
    severity: str


# Package defined types

class BaseDependencyMetadataDict(TypedDict):
    release_date: str
    version: str


class DependencyMetadataDict(BaseDependencyMetadataDict, total=False):
    cpe: Optional[str]
    urls: List[str]
    sha256: str


DependenciesDict = Dict[str, DependencyMetadataDict]
