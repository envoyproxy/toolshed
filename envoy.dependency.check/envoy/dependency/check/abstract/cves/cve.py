"""Abstract CVE."""

import textwrap
from datetime import date
from functools import cached_property
from typing import Set, Type

import jinja2

import abstracts

from envoy.dependency.check import abstract, exceptions, typing

from aio.api import nist


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


class ADependencyCVE(metaclass=abstracts.Abstraction):

    def __init__(
            self,
            cve_data: "typing.DependencyCVEItemDict",
            cpe_class: Type["nist.ACPE"]) -> None:
        self.cve_data = cve_data
        self.cpe_class = cpe_class

    def __gt__(self, other) -> bool:
        return self.id > other.id

    @cached_property
    def cpes(self) -> Set["nist.ACPE"]:
        """Associated CPEs."""
        return set(self.cpe_class(**cpe) for cpe in self.cve_data["cpes"])

    @property
    def description(self) -> str:
        """CVE description."""
        return self.cve_data["description"]

    @cached_property
    def fail_template(self) -> jinja2.Template:
        """Jinja2 template for rendering a failing CVE match."""
        return jinja2.Template(self.fail_tpl)

    @property
    def fail_tpl(self) -> str:
        """Template string, used for rendering with Jinja2."""
        return CVE_FAIL_TPL.lstrip()

    @property
    def formatted_description(self) -> str:
        """Indented CVE description."""
        return '\n  '.join(textwrap.wrap(self.description))

    @property
    def id(self) -> str:
        """CVE id/code."""
        return self.cve_data["id"]

    @property
    def last_modified_date(self) -> date:
        """Date the CVE was last modified."""
        return self.parse_cve_date(self.cve_data['last_modified_date'])

    @property
    def published_date(self) -> date:
        """Date the CVE was published."""
        return self.parse_cve_date(self.cve_data['published_date'])

    @property
    def score(self) -> float:
        """CVE score."""
        return float(self.cve_data["score"])

    @property
    def severity(self) -> str:
        """CVE severity."""
        return self.cve_data["severity"]

    def format_failure(self, dep: "abstract.ADependency") -> str:
        """Format CVE failure for a given dependency."""
        return self.fail_template.render(
            cve=self,
            dependency=dep)

    def parse_cve_date(self, date_str: str) -> date:
        if not date_str.endswith('Z'):
            raise exceptions.CVEError(
                "CVE dates should be UTC and in isoformat")
        return date.fromisoformat(date_str.split('T')[0])
