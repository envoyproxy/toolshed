
import textwrap
from datetime import date
from functools import cached_property
from typing import List, Set, Type

import jinja2

import abstracts

from .cpe import ACPE
from . import typing
from .dependency import ADependency
from .version_matcher import ACVEVersionMatcher


CVE_FAIL_TPL = """
  CVE ID: {{cve.id}} ({{dependency.id}}@{{dependency.version}})
  CVSS v3 score: {{cve.score}}
  Severity: {{cve.severity}}
  Published date: {{cve.published_date}}
  Last modified date: {{cve.last_modified_date}}
  Description: {{cve.formatted_description}}
  Affected CPEs:
{%- for cpe in cve.cpes %}
  - {{cpe}}
{% endfor %}
"""


class ACVE(metaclass=abstracts.Abstraction):

    def __init__(
            self,
            cve_data: "typing.CVEItemDict",
            tracked_cpes: "typing.TrackedCPEDict") -> None:
        self.cve_data = cve_data
        self.tracked_cpes = tracked_cpes

    def __gt__(self, other) -> bool:
        return self.id > other.id

    @property  # type:ignore
    @abstracts.interfacemethod
    def cpe_class(self) -> ACPE:
        raise NotImplementedError

    @cached_property
    def cpes(self) -> Set[ACPE]:
        cpe_set: Set[ACPE] = set()
        self.gather_cpes(self.nodes, cpe_set)
        return cpe_set

    @property
    def description(self) -> str:
        return self.cve_data[
            'cve']['description']['description_data'][0]['value']

    @cached_property
    def fail_template(self) -> jinja2.Template:
        return jinja2.Template(self.fail_tpl)

    @property
    def fail_tpl(self) -> str:
        return CVE_FAIL_TPL.lstrip()

    @property
    def formatted_description(self) -> str:
        return '\n  '.join(textwrap.wrap(self.description))

    @property
    def id(self) -> str:
        return self.cve_data['cve']['CVE_data_meta']['ID']

    @property
    def is_v3(self) -> bool:
        return "baseMetricV3" in self.cve_data['impact']

    @property
    def last_modified_date(self) -> date:
        return self.parse_cve_date(self.cve_data['lastModifiedDate'])

    @property
    def nodes(self) -> List["typing.CVENodeDict"]:
        return self.cve_data['configurations']['nodes']

    @property
    def published_date(self) -> date:
        return self.parse_cve_date(self.cve_data['publishedDate'])

    @property
    def score(self) -> float:
        return self.cve_data['impact']['baseMetricV3']['cvssV3']['baseScore']

    @property
    def severity(self) -> str:
        return self.cve_data[
            'impact']['baseMetricV3']['cvssV3']['baseSeverity']

    @property  # type:ignore
    @abstracts.interfacemethod
    def version_matcher_class(self) -> Type[ACVEVersionMatcher]:
        raise NotImplementedError

    def dependency_match(self, dependency: ADependency) -> bool:
        """Heuristically match dependency metadata against CVE.

        In general, we allow false positives but want to keep the noise
        low, to avoid the toil around having to populate IGNORES_CVES.
        """
        # ? wildcard_version_match = False
        # Consider each CPE attached to the CVE for a match against the
        # dependency CPE.
        for cpe in self.cpes:
            if cpe.dependency_match(dependency):
                # Wildcard version matches need additional heuristics unrelated
                # to CPE to qualify, e.g. last updated date.
                return (
                    self.wildcard_version_match(dependency)
                    if cpe.version == '*'
                    else True)

    def format_failure(self, dependency: ADependency) -> str:
        return self.fail_template.render(
            cve=self,
            dependency=dependency)

    def gather_cpes(
            self,
            nodes: List["typing.CVENodeDict"],
            cpe_set: Set[ACPE]) -> None:
        for node in nodes:
            for cpe_match in node.get('cpe_match', []):
                cpe = self.cpe_class.from_string(cpe_match.pop('cpe23Uri'))
                if self.include_version(cpe_match, cpe):
                    cpe_set.add(cpe)
            children = node.get('children', [])
            if children:
                self.gather_cpes(children, cpe_set)

    def include_version(
            self,
            cpe_match: "typing.CVENodeMatchDict",
            cpe: "ACPE") -> bool:
        return (
            str(cpe) in self.tracked_cpes
            and (
                self.version_matcher_class(cpe_match)(
                    self.tracked_cpes[str(cpe)])))

    def parse_cve_date(self, date_str: str) -> date:
        assert (date_str.endswith('Z'))
        return date.fromisoformat(date_str.split('T')[0])

    def wildcard_version_match(self, dependency: ADependency) -> bool:
        # If the CVE was published after the dependency was last updated, it's
        # a potential match.
        return (
            date.fromisoformat(dependency.release_date)
            <= self.published_date)
