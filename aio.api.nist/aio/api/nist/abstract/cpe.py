"""Abstract CPE."""

from functools import cached_property, lru_cache

import abstracts

from aio.api.nist import exceptions


class ACPE(metaclass=abstracts.Abstraction):
    """Model a subset of CPE fields that are used in CPE matching."""

    @classmethod
    @lru_cache(maxsize=None)
    def from_string(cls, cpe_str: str) -> "ACPE":
        """Generate a CPE object from a CPE string."""
        invalid_string = (
            len(components := cpe_str.split(':')) < 6
            or not cpe_str.startswith('cpe:2.3:'))
        if invalid_string:
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

    def __str__(self) -> str:
        return (
            f"cpe:2.3:{self.part}:{self.vendor}:"
            f"{self.product}:{self.version}")

    @cached_property
    def vendor_normalized(self) -> str:
        """Return a normalized CPE where only part and vendor are
        significant."""
        return str(self.__class__(self.part, self.vendor, '*', '*'))
