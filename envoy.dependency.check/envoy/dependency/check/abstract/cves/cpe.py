"""Abstract CPE."""

import re

import abstracts

from envoy.base import utils

from envoy.dependency.check import abstract, exceptions


FUZZY_DATE_RE = re.compile(r'(\d{4}).?(\d{2}).?(\d{2})')
FUZZY_SEMVER_RE = re.compile(r'(\d+)[:\.\-_](\d+)[:\.\-_](\d+)')


class ADependencyCPE(metaclass=abstracts.Abstraction):
    """Model a subset of CPE fields that are used in CPE matching."""

    @classmethod
    def from_string(cls, cpe_str: str) -> "ADependencyCPE":
        """Generate a CPE object from a CPE string."""
        components = cpe_str.split(':')
        if len(components) < 6 or not cpe_str.startswith('cpe:2.3:'):
            raise exceptions.CPEError(
                f"CPE string ({cpe_str}) must be a valid CPE v2.3 string")
        return cls(*components[2:6])

    def __init__(
            self,
            part: str,
            vendor: str,
            product: str = "*",
            version: str = "*") -> None:
        self.part = part
        self.vendor = vendor
        self.product = product
        self.version = version

    def __str__(self):
        return (
            f"cpe:2.3:{self.part}:{self.vendor}:"
            f"{self.product}:{self.version}")

    @property
    def vendor_normalized(self) -> str:
        """Return a normalized CPE where only part and vendor are
        significant."""
        return str(self.__class__(self.part, self.vendor, '*', '*'))

    def dependency_match(self, dep: "abstract.ADependency") -> bool:
        """Heuristically match dependency metadata against CPE."""
        dep_cpe = self.__class__.from_string(utils.typed(str, dep.cpe))

        # We allow Envoy dependency CPEs to wildcard the 'product', this is
        # useful for
        # LLVM where multiple product need to be covered.
        matching_parts = (
            self.part == dep_cpe.part
            and self.vendor == dep_cpe.vendor
            and (
                dep_cpe.product == '*'
                or self.product == dep_cpe.product))
        if not matching_parts:
            return False

        # TODO: fix/remove remaining - this always evaluates to True
        version_match = (
            # Wildcard versions always match.
            self.version == '*'
            # An exact version match is a hit.
            or self.version == dep.version
            # Allow the 'release_date' dependency metadata to substitute
            # for date.
            # TODO(htuch): Consider fuzzier date ranges.
            or self.version == dep.release_date)
        if version_match:
            return True

        # Try a fuzzy date match to deal with versions like fips-20190304 in
        # dependency version.
        # Or, a fuzzy semver match to deal with things like 2.1.0-beta3.
        # Else, fall-thru (ie False).
        return (
            self.regex_groups_match(
                FUZZY_DATE_RE,
                dep.version,
                self.version)
            or self.regex_groups_match(
                FUZZY_SEMVER_RE,
                dep.version,
                self.version))

    def regex_groups_match(self, regex, lhs, rhs) -> bool:
        """Do two strings match modulo a regular expression?"""
        lhs_match = regex.search(lhs)
        if not lhs_match:
            return False
        rhs_match = regex.search(rhs)
        return bool(
            rhs_match
            and lhs_match.groups() == rhs_match.groups())
