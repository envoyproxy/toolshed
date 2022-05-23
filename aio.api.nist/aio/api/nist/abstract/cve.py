
from datetime import date
from functools import cached_property
from typing import Dict, List, Optional, Set, Type

import abstracts

from aio.api.nist import abstract, typing
from aio.core.functional import QueryDict


class ACVE(metaclass=abstracts.Abstraction):
    """A CVE entry that matches against provided CPEs."""

    @classmethod
    def parse_date(cls, date_str: str) -> date:
        return date.fromisoformat(date_str.split('T')[0])

    def __init__(
            self,
            cve_data: Dict,
            tracked_cpes: "typing.TrackedCPEMatchingDict",
            cpe_class: Type["abstract.ACPE"],
            cve_fields: Optional[QueryDict] = None) -> None:
        self.cve_data = cve_data
        self.tracked_cpes = tracked_cpes
        self.cpe_class = cpe_class
        self.cve_fields = cve_fields

    @cached_property
    def cpes(self) -> Set["abstract.ACPE"]:
        """Associated CPEs."""
        cpe_set: Set["abstract.ACPE"] = set()
        self.gather_cpes(self.nodes, cpe_set)
        return cpe_set

    @cached_property
    def cve_dict(self) -> Dict:
        """Dictionary of parsed information about this CVE."""
        return dict(
            **self.cve_data,
            cpes=self.gathered_cpes)

    @property
    def gathered_cpes(self) -> "typing.CPEsTuple":
        """Tuple of matching CVEs for this CVE."""
        return tuple(
            dict(part=cpe.part,
                 vendor=cpe.vendor,
                 product=cpe.product,
                 version=cpe.version)
            for cpe in self.cpes)

    @property
    def id(self) -> str:
        """CVE ID."""
        return self.cve_data["id"]

    @property
    def nodes(self) -> List["typing.CVENodeDict"]:
        """CVE nodes used for matching versions."""
        return self.cve_data["nodes"]

    @property
    def published_date(self) -> date:
        """Published date of this CVE."""
        return self.parse_date(self.cve_data["published_date"])

    def gather_cpes(
            self,
            nodes: List["typing.CVENodeDict"],
            cpe_set: Set["abstract.ACPE"]) -> None:
        """Recursively gather CPE data from CVE nodes."""
        for node in nodes:
            for cpe_match in node.get('cpe_match', []):
                cpe = self.cpe_class.from_string(cpe_match.pop('cpe23Uri'))
                if self.include_version(cpe_match, cpe):
                    cpe_set.add(cpe)
            if children := node.get('children', []):
                self.gather_cpes(children, cpe_set)

    def include_version(
            self,
            cpe_match: "typing.CVENodeMatchDict",
            cpe: "abstract.ACPE") -> bool:
        """Determine whether a CPE matches according to installed version of a
        dependency."""
        return (
            self.tracked_cpes[str(cpe)](self, cpe, cpe_match)
            if str(cpe) in self.tracked_cpes
            else False)

    def update_fields(self, data) -> "typing.CVEDict":
        """Add requested fields for matched CVE."""
        # todo: if nodes are requested dont delete just rename if required
        del self.cve_dict["nodes"]
        if self.cve_fields:
            self.cve_dict.update(**self.cve_fields(data))
