
import pathlib
import shutil
import subprocess
from functools import cached_property
from typing import Iterable, Optional

import verboselogs  # type:ignore

from envoy.gpg import identity

from .exceptions import SigningError


class DirectorySigningUtil:
    """Base class for signing utils - eg for deb or rpm packages"""

    command_name = ""
    _package_type = ""
    ext = ""

    def __init__(
            self,
            path: pathlib.Path | str,
            maintainer: identity.GPGIdentity,
            log: verboselogs.VerboseLogger,
            command: Optional[str] = ""):
        self._path = path
        self.maintainer = maintainer
        self.log = log
        self._command = command

    @cached_property
    def command(self) -> str:
        """Provided command name/path or path to available system version."""
        command = self._command or shutil.which(self.command_name)
        if command:
            return command
        raise SigningError(
            "Signing software missing "
            f"({self.package_type}): {self.command_name}")

    @property
    def command_args(self) -> tuple:
        return ()

    @property
    def package_type(self) -> str:
        return self._package_type or self.ext

    @property
    def path(self) -> pathlib.Path:
        return pathlib.Path(self._path)

    @property
    def pkg_files(self) -> Iterable[pathlib.Path]:
        """Tuple of paths to package files to sign."""
        # TODO?(phlax): check maintainer/packager field matches key id
        return tuple(
            pkg_file
            for pkg_file
            in self.path.glob("*")
            if pkg_file.name.endswith(f".{self.ext}"))

    def sign(self) -> None:
        """Sign the packages."""
        for pkg in self.pkg_files:
            self.sign_pkg(pkg)

    def sign_command(self, pkg_file: pathlib.Path) -> tuple:
        """Tuple of command parts to sign a specific package."""
        return (self.command,) + self.command_args + (str(pkg_file),)

    def sign_pkg(self, pkg_file: pathlib.Path) -> None:
        """Sign a specific package file."""
        self.log.notice(f"Sign package ({self.package_type}): {pkg_file.name}")
        response = subprocess.run(
            self.sign_command(pkg_file), capture_output=True, encoding="utf-8")

        if response.returncode:
            raise SigningError(response.stdout + response.stderr)

        self.log.success(
            f"Signed package ({self.package_type}): {pkg_file.name}")
