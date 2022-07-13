
import abc
import asyncio
import io
import logging
import pathlib
import tarfile
from collections import defaultdict
from concurrent import futures
from functools import cached_property
from typing import AsyncIterator, List, Optional, Tuple, Type

import aiohttp

import abstracts

from aio.api import nist
from aio.core import event
from aio.core.functional import (
    async_property,
    AwaitableGenerator,
    qdict)

from envoy.base import utils
from envoy.dependency.check import abstract, typing


logger = logging.getLogger(__name__)


@abstracts.implementer(event.IReactive)
class ADependencyCVEs(event.AReactive, metaclass=abstracts.Abstraction):

    def __init__(
            self,
            dependencies: Tuple["abstract.ADependency", ...],
            config_path: Optional[str] = None,
            preloaded_cve_data: Optional[str] = None,
            session: Optional[aiohttp.ClientSession] = None,
            loop: Optional[asyncio.AbstractEventLoop] = None,
            pool: Optional[futures.Executor] = None) -> None:
        self.dependencies = dependencies
        self._config_path = config_path
        self._preloaded_cve_data = preloaded_cve_data
        self._session = session
        self._loop = loop
        self._pool = pool

    @cached_property
    def config(self) -> "typing.CVEConfigDict":
        """CVE scan config - a combination of defaults and config defined
        in provided config file
        """
        return (
            utils.typed(dict, utils.from_yaml(self.config_path))
            if self.config_path
            else {})

    @property
    def config_path(self) -> Optional[pathlib.Path]:
        """Path to CVE scan config file."""
        return (
            pathlib.Path(self._config_path)
            if self._config_path
            else None)

    @property  # type:ignore
    @abstracts.interfacemethod
    def cpe_class(self) -> Type["nist.ACPE"]:
        """CPE class."""
        raise NotImplementedError

    @cached_property
    def cpe_revmap(self) -> "nist.typing.CPERevmapDict":
        return defaultdict(set)

    @property  # type:ignore
    @abstracts.interfacemethod
    def cve_class(self) -> Type["abstract.ADependencyCVE"]:
        """CVE class."""
        raise NotImplementedError

    @property
    def cve_fields(self):
        return qdict(
            score="impact/baseMetricV3/cvssV3/baseScore",
            severity="impact/baseMetricV3/cvssV3/baseSeverity",
            description="cve/description/description_data/0/value",
            last_modified_date="lastModifiedDate")

    @cached_property
    def cves(self) -> "nist.typing.CVEDict":
        return {}

    @async_property(cache=True)
    async def data(self) -> "nist.typing.CVEDataTuple":
        if not await self.loader:
            await AwaitableGenerator(self.downloads)
        return self.cves, self.cpe_revmap

    @async_property
    async def downloads(self) -> AsyncIterator[str]:
        """Yield and optionally download from NIST CVE urls.

        If data is already loaded will just yield the urls, otherwise
        downloads and captures the data.
        """
        if await self.loader:
            for url in self.nist_downloader.urls:
                yield url
            return
        with self.loader:
            async for url in self.nist_downloader:
                yield url
            for id, cve in self.nist_downloader.cves.items():
                self.cves[id] = self.cve_class(cve, self.cpe_class)
            self.cpe_revmap.update(self.nist_downloader.cpe_revmap)

    @property
    @abc.abstractmethod
    def ignored_cves(self) -> List[str]:
        """List of CVEs to ignore, taken from config file."""
        return self.config.get("ignored_cves", [])

    @cached_property
    def loader(self) -> event.ILoader:
        return event.Loader()

    @cached_property
    def nist_downloader(self):
        return self.nist_downloader_class(
            self.tracked_cpes,
            cve_fields=self.cve_fields,
            ignored_cves=self.ignored_cves,
            cve_data=self.preloaded_cve_data,
            since=self.scan_year_start,
            pool=self.pool,
            session=self.session)

    @property  # type:ignore
    @abstracts.interfacemethod
    def nist_downloader_class(self) -> Type["nist.abstract.ANISTDownloader"]:
        """NIST downloader class."""
        raise NotImplementedError

    @property
    def preloaded_cve_data(self) -> Optional[str]:
        return self._preloaded_cve_data

    @property
    def scan_year_start(self) -> Optional[int]:
        """Inclusive start year to scan from."""
        return self.config.get("start_year")

    @cached_property
    def session(self) -> aiohttp.ClientSession:
        """HTTP client session."""
        return self._session or aiohttp.ClientSession()

    @cached_property
    def tracked_cpes(self) -> "nist.typing.TrackedCPEDict":
        """Dict of tracked CPE <> dependency."""
        return {
            v.cpe: self.cpe_filter_dict(v)
            for v
            in self.dependencies
            if v.cpe}

    def cpe_filter_dict(
            self,
            dependency: "abstract.ADependency") -> (
                "nist.typing.TrackedCPEFilterDict"):
        """Provide filter args to filter out non-matching CPEs."""
        return dict(
            version=dependency.release_version,
            date=dependency.release_date)

    async def dependency_check(
            self,
            dep: "abstract.ADependency") -> AsyncIterator[
                "abstract.ADependencyCVE"]:
        """Check for relevant CVEs for a given dep."""
        if not dep.cpe:
            return
        cves, cpe_revmap = await self.data
        cpe = self.cpe_class.from_string(dep.cpe).vendor_normalized
        for cpe_cve in sorted(cpe_revmap.get(cpe, [])):
            yield cves[cpe_cve]

    async def download_cves(self, path: str) -> None:
        with tarfile.open(path, "w") as tar:
            for url in self.nist_downloader.urls:
                response = await self.nist_downloader.download(url)
                data = io.BytesIO(await response.read())
                info = tarfile.TarInfo(name=url.split("/")[-1])
                info.size = len(data.getvalue())
                tar.addfile(info, fileobj=data)
