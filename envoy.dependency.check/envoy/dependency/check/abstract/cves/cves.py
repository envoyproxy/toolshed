
import abc
import gzip
import json
import pathlib
from collections import defaultdict
from datetime import datetime
from functools import cached_property
from typing import AsyncIterator, Dict, List, Optional, Tuple

import aiohttp

import abstracts

from aio.core.functional import async_property
from aio.core.tasks import concurrent

from envoy.base import utils
from envoy.dependency.check import abstract, exceptions, typing

NIST_URL_TPL = (
    "https://nvd.nist.gov/feeds/json/cve/1.1/nvdcve-1.1-{year}.json.gz")
SCAN_FROM_YEAR = 2018


class ADependencyCVEs(metaclass=abstracts.Abstraction):

    def __init__(
            self,
            dependencies: Tuple["abstract.ADependency", ...],
            config_path: Optional[str] = None,
            session: Optional[aiohttp.ClientSession] = None) -> None:
        self.dependencies = dependencies
        self._config_path = config_path
        self._session = session

    @cached_property
    def config(self) -> "typing.CVEConfigDict":
        """CVE scan config - a combination of defaults and config defined
        in provided config file
        """
        config: "typing.CVEConfigDict" = dict(
            nist_url=self.nist_url_tpl,
            start_year=self.start_year or 0)
        config.update(self.user_config)  # type:ignore
        if config["start_year"] == 0:
            raise exceptions.CVECheckError(
                "`start_year` must be specified in config "
                f"({self.config_path}) or implemented by "
                f"`{self.__class__.__name__}`")
        return config

    @property
    def config_path(self) -> Optional[pathlib.Path]:
        """Path to CVE scan config file."""
        return (
            pathlib.Path(self._config_path)
            if self._config_path
            else None)

    @property  # type:ignore
    @abstracts.interfacemethod
    def cpe_class(self) -> "abstract.ADependencyCPE":
        """CPE class."""
        raise NotImplementedError

    @cached_property
    def cpe_revmap(self) -> "typing.CPERevmapDict":
        return defaultdict(set)

    @property  # type:ignore
    @abstracts.interfacemethod
    def cve_class(self) -> "abstract.ADependencyCVE":
        """CVE class."""
        raise NotImplementedError

    @cached_property
    def cves(self) -> "typing.CVEDict":
        return {}

    @async_property(cache=True)
    async def data(self) -> "typing.CVEDataTuple":
        if not self.cves:
            async for download in self.downloads:
                pass
        return self.cves, self.cpe_revmap

    @async_property
    async def downloads(self) -> AsyncIterator[str]:
        """CVE data derived from parsing NIST CVE data."""
        async for download in concurrent(self.nist_downloads):
            yield download.url
            await self.parse_cve_response(download)

    @property
    @abc.abstractmethod
    def ignored_cves(self) -> List[str]:
        """List of CVEs to ignore, taken from config file."""
        return self.config.get("ignored_cves", [])

    @property
    def nist_downloads(self) -> "typing.DownloadGenerator":
        """Download co-routines for NIST data."""
        for url in self.urls:
            yield self.download(url)

    @property
    def nist_url_tpl(self) -> str:
        """Default URL template string for NIST downloads."""
        return NIST_URL_TPL

    @property
    def scan_year_end(self) -> int:
        """Inclusive end year to scan to."""
        return datetime.now().year + 1

    @property
    def scan_year_start(self) -> int:
        """Inclusive start year to scan from."""
        return self.config["start_year"]

    @property
    def scan_years(self) -> range:
        """Range of years to scan."""
        return range(self.scan_year_start, self.scan_year_end)

    @cached_property
    def session(self) -> aiohttp.ClientSession:
        """HTTP client session."""
        return self._session or aiohttp.ClientSession()

    @property
    def start_year(self) -> int:
        """Start year to scan from, override this to remove requirement to
        specify `start_year` in config."""
        return SCAN_FROM_YEAR

    @cached_property
    def tracked_cpes(self) -> "typing.TrackedCPEDict":
        """Dict of tracked CPE <> dependency."""
        return {
            v.cpe: v
            for v
            in self.dependencies
            if v.cpe}

    @property
    def urls(self) -> List[str]:
        """URLs to fetch NIST data from."""
        return [
            self.config["nist_url"].format(year=year)
            for year in self.scan_years]

    @property
    def user_config(self) -> Dict:
        return (
            utils.typed(dict, utils.from_yaml(self.config_path))
            if self.config_path
            else {})

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
            if cves[cpe_cve].dependency_match(dep):
                yield cves[cpe_cve]

    async def download(self, url: str) -> aiohttp.ClientResponse:
        """Async HTTP get of download URL."""
        return await self.session.get(url)

    def include_cve(self, cve) -> bool:
        """Determine whether a CVE has any (not-ignored) CPEs."""
        return bool(
            len(cve.cpes) > 0
            and cve.is_v3
            and cve.id not in self.ignored_cves)

    def parse_cve_json(
            self,
            cve_json: "typing.CVEJsonDict"):
        """Parse CVE JSON dictionary."""
        for cve_item in cve_json['CVE_Items']:
            cve = self.cve_class(cve_item, self.tracked_cpes)
            if not self.include_cve(cve):
                continue
            self.cves[cve.id] = cve
            for cve_cpe in cve.cpes:
                self.cpe_revmap[cve_cpe.vendor_normalized].add(cve.id)

    async def parse_cve_response(
            self,
            download: aiohttp.ClientResponse) -> None:
        """Parse async gzipped HTTP response -> JSON."""
        dl_exceptions = (
            aiohttp.client_exceptions.ClientPayloadError,
            gzip.BadGzipFile)
        try:
            self.parse_cve_json(
                json.loads(gzip.decompress(await download.read())))
        except dl_exceptions as e:
            raise exceptions.CVECheckError(
                f"Error downloading from {download.url}: {e}")
