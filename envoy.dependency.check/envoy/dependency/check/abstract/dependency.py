"""Abstract dependency."""

from functools import cached_property
from typing import Optional

from packaging import version

import abstracts

from envoy.dependency.check import typing


class ADependency(metaclass=abstracts.Abstraction):
    """Github dependency."""

    def __init__(
            self,
            id: str,
            metadata: "typing.DependencyMetadataDict") -> None:
        self.id = id
        self.metadata = metadata

    def __gt__(self, other: "ADependency") -> bool:
        return self.id > other.id

    def __lt__(self, other: "ADependency") -> bool:
        return self.id < other.id

    def __str__(self):
        return f"{self.id}@{self.version}"

    @cached_property
    def cpe(self) -> Optional[str]:
        """Configured CPE for this dependency."""
        return (
            str(self.metadata["cpe"])
            if self.metadata.get("cpe", "N/A") != "N/A"
            else None)

    @property
    def release_date(self) -> str:
        """Release (or published) date of this dependency."""
        return self.metadata["release_date"]

    @cached_property
    def release_version(self) -> Optional[version.Version]:
        """Semantic version for the release of this dependency if available."""
        try:
            return version.Version(self.version)
        except version.InvalidVersion:
            return None

    @property
    def version(self) -> str:
        """Version string of this dependency."""
        return self.metadata["version"]
