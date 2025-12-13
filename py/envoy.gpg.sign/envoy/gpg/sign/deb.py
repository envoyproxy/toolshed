
import pathlib
from functools import cached_property
from itertools import chain
from typing import Iterator, Type

from .exceptions import SigningError
from .util import DirectorySigningUtil


class DebChangesFiles(object):
    """Creates a set of `changes` files for specific distros from a src
    `changes` file.

    eg, if src changes file is `envoy_1.100.changes` and `Distribution:`
    field is `buster bullseye`, it creates:

        `envoy_1.100.changes` -> `envoy_1.100.buster.changes`
        `envoy_1.100.changes` -> `envoy_1.100.bullseye.changes`

    while replacing any instances of the original distribution name in
    the respective changes files, eg:

        `buster bullseye` -> `buster`
        `buster bullseye` -> `bullseye`

    finally, it removes the src changes file.
    """

    def __init__(self, src):
        self.src = src

    def __iter__(self) -> Iterator[pathlib.Path]:
        """Iterate the required changes files, creating them, yielding the
        paths of the newly created files, and deleting the original."""
        for path in self.files:
            yield path
        self.src.unlink()

    @cached_property
    def distributions(self) -> str:
        """Find and parse the `Distributions` header in the `changes` file."""
        with open(self.src) as f:
            line = f.readline()
            while line:
                if not line.startswith("Distribution:"):
                    line = f.readline()
                    continue
                return line.split(":")[1].strip()
        raise SigningError(
            f"Did not find Distribution field in changes file {self.src}")

    @property
    def files(self) -> Iterator[pathlib.Path]:
        """Create changes files for each distro, yielding the paths."""
        for distro in self.distributions.split():
            yield self.changes_file(distro)

    def changes_file(self, distro: str) -> pathlib.Path:
        """Create a `changes` file for a specific distro."""
        target = self.changes_file_path(distro)
        target.write_text(
            self.src.read_text().replace(
                self.distributions,
                distro))
        return target

    def changes_file_path(self, distro: str) -> pathlib.Path:
        """Path to write the new changes file to."""
        return self.src.with_suffix(f".{distro}.changes")


class DebSigningUtil(DirectorySigningUtil):
    """Sign all `changes` packages in a given directory.

    the `.changes` spec allows a single `.changes` file to have multiple
    `Distributions` listed.

    but, most package repos require a single signed `.change` file per
    distribution, with only one distribution listed.

    this extracts the `.changes` files to -> per-distro
    `filename.distro.changes`, and removes the original, before signing the
    files.
    """

    command_name = "debsign"
    ext = "changes"
    _package_type = "deb"

    @cached_property
    def command_args(self) -> tuple:
        return ("-k", self.maintainer.fingerprint)

    @property
    def changes_files(self) -> Type[DebChangesFiles]:
        return DebChangesFiles

    @cached_property
    def pkg_files(self) -> tuple:
        """Mangled .changes paths."""
        return tuple(
            chain.from_iterable(
                self.changes_files(src)
                for src in super().pkg_files))
