
import hashlib
import pathlib
from functools import cached_property
from typing import Iterator

from .util import DirectorySigningUtil


class BinarySigningUtil(DirectorySigningUtil):
    """Sign all `changes` packages in a given directory.

    the `.changes` spec allows a single `.changes` file to have multiple
    `Distributions` listed.

    but, most package repos require a single signed `.change` file per
    distribution, with only one distribution listed.

    this extracts the `.changes` files to -> per-distro
    `filename.distro.changes`, and removes the original, before signing the
    files.
    """

    _package_type = "bin"

    @cached_property
    def pkg_files(self) -> Iterator[pathlib.Path]:
        return self.path.glob("*")

    @cached_property
    def shas(self):
        shas = dict()
        for pkg in self.pkg_files:
            shas[pkg] = self.sha256sum(pkg)
        return shas

    @property
    def checksum_path(self):
        return self.path.joinpath("checksums.txt.asc")

    @property
    def checksums(self):
        return "\n".join(f"{sha}  {path}" for path, sha in self.shas.items())

    def sign(self) -> None:
        """Sign the packages."""
        # make sure correct key
        signed = self.maintainer.gpg.sign(self.checksums, clearsign=True).data
        print(signed.decode("utf-8"))
        self.checksum_path.write_bytes(signed)

    def sha256sum(self, pkg_file: pathlib.Path) -> str:
        """Sign a specific package file."""
        sha = hashlib.sha256(pkg_file.read_bytes()).hexdigest()
        self.log.notice(
            f"Sign package ({self.package_type}): "
            f"{pkg_file.name} {sha}")
        return sha
