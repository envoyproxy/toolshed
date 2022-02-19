"""NIST CVE data downloader."""

import asyncio
import logging
from concurrent import futures
from datetime import datetime
from functools import cached_property
from typing import AsyncIterator, Optional, Set, Type

import aiohttp

import abstracts

from aio.core import event
from aio.core.functional import async_property, QueryDict
from aio.core.tasks import concurrent

from aio.api.nist import abstract, typing


logger = logging.getLogger(__name__)

NIST_URL_TPL = (
    "https://nvd.nist.gov/feeds/json/cve/1.1/nvdcve-1.1-{year}.json.gz")
SCAN_FROM_YEAR = 2018


@abstracts.implementer(event.IExecutive)
class ANISTDownloader(event.AExecutive, metaclass=abstracts.Abstraction):

    def __init__(
            self,
            tracked_cpes: "typing.TrackedCPEDict",
            cve_fields: Optional[QueryDict] = None,
            ignored_cves: Optional[Set] = None,
            since: Optional[int] = None,
            loop: Optional[asyncio.AbstractEventLoop] = None,
            pool: Optional[futures.Executor] = None,
            session: Optional[aiohttp.ClientSession] = None) -> None:
        self._since = since
        self.cve_fields = cve_fields
        self.ignored_cves = ignored_cves
        self.tracked_cpes = tracked_cpes
        self._session = session
        self._loop = loop
        self._pool = pool

    async def __aiter__(self) -> AsyncIterator[str]:
        async for url in self.downloads:
            yield url

    @cached_property
    def cpe_revmap(self) -> "typing.CPERevmapDict":
        """Collected reverse mapping of CPEs."""
        return {}

    @cached_property
    def cves(self) -> "typing.CVEDict":
        """Collected CVEs."""
        return {}

    @property
    def downloaders(self) -> "typing.DownloadGenerator":
        """Download co-routines for NIST data."""
        for url in self.urls:
            yield self.download_and_parse(url)

    @async_property
    async def downloads(self) -> AsyncIterator[str]:
        """CVE data derived from parsing NIST CVE data."""
        async for download in concurrent(self.downloaders):
            yield download.url

    @property
    def nist_url_tpl(self) -> str:
        """Default URL template string for NIST downloads."""
        return NIST_URL_TPL

    @cached_property
    def parser(self) -> "abstract.ANISTParser":
        """NIST CVE parser, to be run in processor pool."""
        return self.parser_class(
            self.tracked_cpes,
            cve_fields=self.cve_fields,
            ignored_cves=self.ignored_cves)

    @property  # type:ignore
    @abstracts.interfacemethod
    def parser_class(self) -> Type["abstract.ANISTParser"]:
        """NIST parser class."""
        raise NotImplementedError

    @property
    def scan_year_end(self) -> int:
        """Inclusive end year to scan to."""
        return datetime.now().year + 1

    @cached_property
    def session(self) -> aiohttp.ClientSession:
        """HTTP client session."""
        return self._session or aiohttp.ClientSession()

    @property
    def since(self) -> int:
        return max(
            self._since or SCAN_FROM_YEAR,
            SCAN_FROM_YEAR)

    @property
    def urls(self) -> Set[str]:
        """URLs to fetch NIST data from."""
        return set(
            self.nist_url_tpl.format(year=year)
            for year
            in self.years)

    @property
    def years(self) -> range:
        """Range of years to scan."""
        return range(
            self.since,
            self.scan_year_end)

    def add(
            self,
            cves: "typing.CVEDict",
            cpe_revmap: "typing.CPERevmapDict") -> None:
        """Capture incoming CVE data."""
        self.cves.update(cves)
        self.cpe_revmap.update(cpe_revmap)

    async def download_and_parse(self, url: str) -> aiohttp.ClientResponse:
        """Async download and parsing of CVE data."""
        download = await self.session.get(url)
        logger.debug(f"Downloading CVE data: {url}")
        self.add(*await self.parse(url, await download.read()))
        logger.debug(f"CVE data saved: {url}")
        return download

    async def parse(self, url: str, data: bytes) -> "typing.CVEDataTuple":
        """Parse incoming data in executor."""
        # Disable this comment to prevent running the parser in a separate
        # process - useful for debugging.
        # return self.parser(data)
        logger.debug(f"Parsing CVE data: {url}")
        return await self.execute(
            self.parser,
            data)
