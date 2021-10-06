
import abc
import argparse
import gzip
import json
import pathlib
from collections import defaultdict
from datetime import datetime
from functools import cached_property
from typing import Generator, List, Optional, Type

import aiohttp

import abstracts

from aio.functional import async_property
from aio.tasks import concurrent

from envoy.base import checker, utils

from ..exceptions import CVECheckError
from . import typing
from .cpe import ACPE
from .cve import ACVE
from .dependency import ADependency


NIST_URL_TPL = (
    "https://nvd.nist.gov/feeds/json/cve/1.1/nvdcve-1.1-{year}.json.gz")
SCAN_FROM_YEAR = 2018


class ACVEChecker(checker.AsyncChecker, metaclass=abstracts.Abstraction):
    checks = ("cves",)

    @cached_property
    def config(self) -> typing.CVEConfigDict:
        config: typing.CVEConfigDict = dict(
            nist_url=self.nist_url_tpl,
            start_year=0)
        config.update(utils.typed(dict, utils.from_yaml(self.config_path)))
        if config["start_year"] == 0:
            try:
                config["start_year"] = self.start_year
            except NotImplementedError:
                raise CVECheckError(
                    "`start_year` must be specified in config "
                    f"({self.config_path}) or implemented by "
                    f"`{self.__class__.__name__}`")
        return config

    @property
    def config_path(self) -> pathlib.Path:
        return pathlib.Path(self.args.config_path)

    @property  # type:ignore
    @abstracts.interfacemethod
    def cpe_class(self) -> ACPE:
        raise NotImplementedError

    @property  # type:ignore
    @abstracts.interfacemethod
    def cve_class(self) -> ACVE:
        raise NotImplementedError

    @async_property
    async def cve_data(self) -> typing.CVEDataTuple:
        cves: typing.CVEDict = dict()
        cpe_revmap: typing.CPERevmapDict = defaultdict(set)
        async for download in concurrent(self.nist_downloads):
            self.log.info(f"CVE data downloaded from: {download.url}")
            await self.parse_cve_response(download, cves, cpe_revmap)
        return cves, cpe_revmap

    @cached_property
    def dependencies(self) -> List[ADependency]:
        return [
            self.dependency_class(k, v)
            for k, v in self.dependency_metadata.items()]

    @property  # type:ignore
    @abstracts.interfacemethod
    def dependency_class(self) -> Type[ADependency]:
        raise NotImplementedError

    @property  # type:ignore
    @abstracts.interfacemethod
    def dependency_metadata(self) -> typing.DependenciesDict:
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def ignored_cves(self) -> List[str]:
        return self.config.get("ignored_cves", [])

    @property
    def nist_downloads(self) -> typing.DownloadGenerator:
        for url in self.urls:
            yield self.download(url)

    @property
    def nist_url_tpl(self) -> str:
        return NIST_URL_TPL

    @property
    def provided_urls(self) -> Optional[List[str]]:
        return self.args.urls

    @property
    def scan_year_end(self) -> int:
        return datetime.now().year + 1

    @property
    def scan_year_start(self) -> int:
        return self.config["start_year"]

    @property
    def scan_years(self) -> range:
        return range(self.scan_year_start, self.scan_year_end)

    @cached_property
    def session(self) -> aiohttp.ClientSession:
        return aiohttp.ClientSession()

    @property
    def start_year(self) -> int:
        raise NotImplementedError

    @cached_property
    def tracked_cpes(self) -> "typing.TrackedCPEDict":
        return {
            v.cpe: v
            for v
            in self.dependencies
            if v.cpe}

    @property
    def urls(self) -> List[str]:
        if self.provided_urls:
            return self.provided_urls
        return [
            self.config["nist_url"].format(year=year)
            for year in self.scan_years]

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("config_path")
        parser.add_argument("urls", nargs="*")
        super().add_arguments(parser)

    async def check_cves(self) -> None:
        """Scan for CVEs in a parsed NIST CVE database."""
        cve_data = await self.cve_data
        for dependency in self.dependencies:
            if not dependency.cpe:
                self.log.info(f"No CPE listed for: {dependency.id}")
                continue
            errors = []
            for cve in sorted(self.dependency_check(dependency, *cve_data)):
                errors.append(
                    f'{cve_data[0][cve].format_failure(dependency)}')
            if errors:
                self.error("cves", errors)
            else:
                self.succeed("cves", [f"No CVEs found for: {dependency.id}"])

    def dependency_check(
            self,
            dependency: ADependency,
            cves: "typing.CVEDict",
            cpe_revmap: "typing.CPERevmapDict") -> Generator:
        cpe_str = self.cpe_class.from_string(dependency.cpe).vendor_normalized
        for cve in cpe_revmap.get(cpe_str, []):
            if cves[cve].dependency_match(dependency):
                yield cve

    async def download(self, url: str) -> aiohttp.ClientResponse:
        return await self.session.get(url)

    def include_cve(self, cve):
        return (
            len(cve.cpes) > 0
            and cve.is_v3
            and cve.id not in self.ignored_cves)

    async def on_checks_complete(self) -> int:
        await self.session.close()
        return await super().on_checks_complete()

    def parse_cve_json(
            self,
            cve_json: "typing.CVEJsonDict",
            cves: "typing.CVEDict",
            cpe_revmap: "typing.CPERevmapDict") -> None:
        """Parse CVE JSON dictionary."""
        for cve_item in cve_json['CVE_Items']:
            cve = self.cve_class(cve_item, self.tracked_cpes)
            if not self.include_cve(cve):
                continue
            cves[cve.id] = cve
            for cpe in cve.cpes:
                cpe_revmap[cpe.vendor_normalized].add(cve.id)

    async def parse_cve_response(
            self,
            download: aiohttp.ClientResponse,
            cves: "typing.CVEDict",
            cpe_revmap: "typing.CPERevmapDict") -> None:
        exceptions = (
            aiohttp.client_exceptions.ClientPayloadError,
            gzip.BadGzipFile)
        try:
            self.parse_cve_json(
                json.loads(gzip.decompress(await download.read())),
                cves,
                cpe_revmap)
        except exceptions as e:
            raise CVECheckError(
                f"Error downloading from {download.url}: {e}")
