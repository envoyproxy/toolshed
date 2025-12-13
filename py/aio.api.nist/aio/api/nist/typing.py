from datetime import date
from typing import (
    Any, Coroutine, Dict, Generator, List, Optional, Set,
    Tuple, TypedDict, Union)

from packaging import version

import aiohttp

from aio.api.nist import abstract, interface, typing


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
    id: str
    configurations: CVEItemConfigurationsDict
    cve: Dict
    impact: Dict


class CVEJsonDict(TypedDict, total=False):
    CVE_Items: List[CVEItemDict]


class TrackedCPEFilterDict(TypedDict, total=False):
    version: Optional[version.Version]
    date: Optional[str]


class TrackedCPEMatchingFilterDict(TypedDict, total=False):
    version: Optional[version.Version]
    date: Optional[date]
    cpe: "abstract.ACPE"


class CPEDict(TypedDict):
    part: str
    product: str
    vendor: str
    version: str


CPEsTuple = Tuple[CPEDict, ...]
CPERevmapDict = Dict[str, Set[str]]
CVEDict = Dict[str, Dict]
CVEQueryDict = Dict[str, Dict]
CVEDataTuple = Tuple[CVEDict, CPERevmapDict]
TrackedCPEDict = Dict[str, TrackedCPEFilterDict]
TrackedCPEMatchingDict = Dict[str, "abstract.ACVEMatcher"]
DownloadGenerator = Generator[
    Coroutine[
        Any,
        Any,
        Union[
            aiohttp.ClientResponse,
            "interface.IPredownload"]],
    str,
    None]
