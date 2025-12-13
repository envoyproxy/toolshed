"""Abstract matcher for CVEs."""

import logging
from datetime import date
from typing import Dict, Optional

from packaging import version

import abstracts

from aio.core.functional import utils

from aio.api.nist import abstract, typing


logger = logging.getLogger(__name__)


class ACVEMatcher(metaclass=abstracts.Abstraction):
    """Matcher for CVEs against date and version."""

    def __init__(
            self,
            filter_dict: typing.TrackedCPEMatchingFilterDict) -> None:
        self._filter_dict = filter_dict

    def __call__(
            self,
            cve: "abstract.ACVE",
            cpe: "abstract.ACPE",
            cpe_match: "typing.CVENodeMatchDict") -> bool:
        matched = self.match_cpe(cve, cpe, cpe_match)
        logger.debug(
            f"Matched\n  {self._match_debug(cve, cpe, cpe_match)}"
            if matched
            else f"No match\n  {self._match_debug(cve, cpe, cpe_match)}")
        return matched

    def __str__(self) -> str:
        return "/".join([
            self._truncate_cpe(self.tracked_cpe),
            str(self.tracked_date),
            str(self.tracked_version)])

    @property
    def tracked_cpe(self) -> "abstract.ACPE":
        """Tracked CPE object to match against."""
        return self._filter_dict["cpe"]

    @property
    def tracked_date(self) -> Optional[date]:
        """Publication date of tracked CPE (optional)."""
        return self._filter_dict["date"]

    @property
    def tracked_version(self) -> Optional[version.Version]:
        """Version of tracked CPE (optional)."""
        return self._filter_dict.get("version")

    def get_version_info(
            self,
            cpe_match: "typing.CVENodeMatchDict") -> Dict[
                str,
                Optional[version.Version]]:
        """Dictionary of mangled start/end versions for a CVE."""
        return {
            f"{action}_{ending}": self._cpe_version(cpe_match, action, ending)
            for action in ["end", "start"]
            for ending in ["exc", "inc"]}

    def match_cpe(
            self,
            cve: "abstract.ACVE",
            cpe: "abstract.ACPE",
            cpe_match: "typing.CVENodeMatchDict") -> bool:
        return bool(
            self.match_date(cve, cpe, cpe_match)
            and self.match_parts(cve, cpe, cpe_match)
            and self.match_version(cve, cpe, cpe_match))

    def match_date(
            self,
            cve: "abstract.ACVE",
            cpe: "abstract.ACPE",
            cpe_match: "typing.CVENodeMatchDict") -> bool:
        """Check whether date for provided CVE/CPE data matches the tracked
        date."""
        return not (
            self.tracked_date
            and (cpe.version == "*"
                 and (cve.published_date
                      < self.tracked_date)))

    def match_parts(
            self,
            cve: "abstract.ACVE",
            cpe: "abstract.ACPE",
            cpe_match: "typing.CVENodeMatchDict") -> bool:
        return (
            cpe.part == self.tracked_cpe.part
            and cpe.vendor == self.tracked_cpe.vendor
            and (
                self.tracked_cpe.product == "*"
                or cpe.product == self.tracked_cpe.product))

    def match_version(
            self,
            cve: "abstract.ACVE",
            cpe: "abstract.ACPE",
            cpe_match: "typing.CVENodeMatchDict") -> bool:
        """Check whether version for provided CVE/CPE data matches the tracked
        version."""
        if not self.tracked_version:
            return True
        version_info = self.get_version_info(cpe_match)
        return not (
            (version_info["end_exc"] is not None
             and self.tracked_version >= version_info["end_exc"])
            or (version_info["end_inc"] is not None
                and self.tracked_version > version_info["end_inc"])
            or (version_info["start_exc"] is not None
                and self.tracked_version <= version_info["start_exc"])
            or (version_info["start_inc"] is not None
                and self.tracked_version < version_info["start_inc"]))

    def _cpe_version(
            self,
            cpe_match: "typing.CVENodeMatchDict",
            action: str,
            ending: str) -> Optional[version.Version]:
        """Transform a cpe version match key -> semantic version."""
        version_info = cpe_match.get(
            f"version{action.capitalize()}{ending.capitalize()}luding", None)
        return (
            version.Version(utils.typed(str, version_info))
            if version_info is not None
            else None)

    def _match_debug(
            self,
            cve: "abstract.ACVE",
            cpe: "abstract.ACPE",
            cpe_match: "typing.CVENodeMatchDict") -> str:
        match_info = "/".join([
            cve.id,
            self._truncate_cpe(cpe),
            str(cve.published_date),
            str(cpe_match)])
        return f"{self}\n  -> {match_info}"

    def _truncate_cpe(
            self,
            cpe: "abstract.ACPE") -> str:
        return str(cpe).split(":", 2)[2]
