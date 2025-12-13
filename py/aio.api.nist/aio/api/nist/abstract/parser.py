"""NIST CVE data parser."""

import logging
from datetime import date
from functools import cached_property
from typing import Dict, Iterator, List, Optional, Set, Tuple, Type

import abstracts

from aio.api.nist import abstract, typing
from aio.core.functional import utils, qdict, QueryDict


logger = logging.getLogger(__name__)


class ANISTParser(metaclass=abstracts.Abstraction):
    """Sync blocking CVE data parser.

    Run me in an executor!.
    """

    def __init__(
            self,
            tracked_cpes: "typing.TrackedCPEDict",
            cve_fields: Optional[QueryDict] = None,
            ignored_cves: Optional[Set] = None) -> None:
        self._tracked_cpes = tracked_cpes
        self.ignored_cves = ignored_cves or set()
        self.cve_fields = cve_fields

    def __call__(
            self,
            data: bytes) -> "typing.CVEDataTuple":
        """Slow, blocking parser."""
        return self.parse_cve_data(data)

    @property  # type:ignore
    @abstracts.interfacemethod
    def cpe_class(self) -> "abstract.ACPE":
        """CPE class."""
        raise NotImplementedError

    @cached_property
    def cpe_revmap(self) -> "typing.CPERevmapDict":
        """Collected reverse mapping of CPEs."""
        return {}

    @property  # type:ignore
    @abstracts.interfacemethod
    def cve_class(self) -> "abstract.ACVE":
        """CVE class."""
        raise NotImplementedError

    @cached_property
    def cves(self) -> "typing.CVEDict":
        """Collected CVEs."""
        return {}

    @property  # type:ignore
    @abstracts.interfacemethod
    def matcher_class(self) -> Type["abstract.ACVEMatcher"]:
        """Version matcher class."""
        raise NotImplementedError

    @cached_property
    def query_fields(self) -> "QueryDict":
        """Fields used for initial matching of the CVE."""
        return qdict(
            id="cve/CVE_data_meta/ID",
            nodes="configurations/nodes",
            published_date="publishedDate")

    @cached_property
    def tracked_cpes(self) -> "typing.TrackedCPEMatchingDict":
        """Mapping of tracked CPEs, with a filter dictionary for matching."""
        return {
            k: self._tracked_cpe(k, v)
            for k, v
            in self._tracked_cpes.items()}

    def add_cpe_revmap(self, cve: "abstract.ACVE") -> None:
        """Add a CVE item to the CPE reverse mapping."""
        for cve_cpe in cve.cpes:
            self.cpe_revmap[cve_cpe.vendor_normalized] = self.cpe_revmap.get(
                cve_cpe.vendor_normalized, set())
            self.cpe_revmap[cve_cpe.vendor_normalized].add(cve.id)

    def add_cve(
            self,
            cve_item: "typing.CVEItemDict",
            cve_data: Dict) -> None:
        """Add CVE to the the cve list if it has relevant CPEs."""
        cve = self.cve_class(
            cve_data,
            self.tracked_cpes,
            self.cpe_class,
            self.cve_fields)
        if not cve.cpes:
            return
        cve.update_fields(cve_item)
        self.add_cpe_revmap(cve)
        self.cves[cve.id] = cve.cve_dict

    def include_cve(self, cve: "typing.CVEItemDict") -> bool:
        """Determine whether the CVE should be included for further
        analysis."""
        if not cve["configurations"]["nodes"]:
            # This will not have any CPEs - not sure what type of record it is
            return False
        is_v3 = bool(cve['impact'].get('baseMetricV3'))
        id = cve['cve']['CVE_data_meta']['ID']
        if is_v3 and id not in self.ignored_cves:
            return True
        logger.debug(
            f"Excluding {id} "
            f"(v3: {is_v3})")
        return False

    def iter_cve_json(
            self,
            data: bytes) -> Iterator[
                Tuple["typing.CVEItemDict",
                      "typing.CVEQueryDict"]]:
        """List of CVE dicts with information required to parse CPEs and
        filter."""
        for cve_item in self._junzip_items(data):
            if self.include_cve(cve_item):
                cve_data = self.query_fields(cve_item)
                # This is too verbose, but can be helpful for debugging
                # logger.debug(f"Analyze CVE {parsed['id']}")
                yield cve_item, cve_data

    def parse_cve_data(
            self,
            data: bytes) -> "typing.CVEDataTuple":
        """Parse CVE JSON dictionary."""
        for cve_item, cve_data in self.iter_cve_json(data):
            self.add_cve(cve_item, cve_data)
        return self.cves, self.cpe_revmap

    def _iso_date(self, date_str: Optional[str]) -> Optional[date]:
        return (
            self.cve_class.parse_date(date_str)
            if date_str
            else None)

    def _junzip_items(self, data: bytes) -> List["typing.CVEItemDict"]:
        return utils.junzip(data)["CVE_Items"]

    def _tracked_cpe(
            self,
            cpe_name: str,
            cpe_filter: typing.TrackedCPEFilterDict) -> (
                "abstract.ACVEMatcher"):
        match_dict: typing.TrackedCPEMatchingFilterDict = dict(
            version=cpe_filter.get("version"),
            cpe=self.cpe_class.from_string(cpe_name),
            date=self._iso_date(cpe_filter.get("date")))
        return self.matcher_class(match_dict)
