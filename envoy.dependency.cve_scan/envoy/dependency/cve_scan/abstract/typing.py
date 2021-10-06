
from typing import (
    Any, Coroutine, Dict, Generator, List, Optional, Set,
    Tuple, TypedDict)

import aiohttp

from . import cve, dependency, typing


# Scanner configuration

class BaseCVEConfigDict(TypedDict):
    # non-optional attributes
    nist_url: str
    start_year: int


class CVEConfigDict(BaseCVEConfigDict, total=False):
    ignored_cves: List[str]


# NDIST CVE data format

class CVENodeMatchDict(TypedDict, total=False):
    cpe23Uri: str
    versionStartIncluding: str
    versionEndIncluding: str
    versionStartExcluding: str
    versionEndExcluding: str


class CVENodeDict(TypedDict, total=False):
    cpe_match: List[CVENodeMatchDict]
    children: List["typing.CVENodeDict"]  # type:ignore


class CVEItemConfigurationsDict(TypedDict, total=False):
    nodes: List[CVENodeDict]


class CVEItemDict(TypedDict, total=False):
    configurations: CVEItemConfigurationsDict
    cve: Dict
    impact: Dict
    lastModifiedDate: str
    publishedDate: str


class CVEJsonDict(TypedDict, total=False):
    CVE_Items: List[CVEItemDict]


# Package defined types

class BaseDependencyMetadataDict(TypedDict):
    release_date: str
    version: str


class DependencyMetadataDict(BaseDependencyMetadataDict, total=False):
    cpe: Optional[str]


CPERevmapDict = Dict[str, Set[str]]
CVEDict = Dict[str, "cve.ACVE"]
CVEDataTuple = Tuple[CVEDict, CPERevmapDict]
DependenciesDict = Dict[str, DependencyMetadataDict]
TrackedCPEDict = Dict[str, "dependency.ADependency"]
DownloadGenerator = Generator[
    Coroutine[Any, Any, aiohttp.ClientResponse],
    str,
    None]
