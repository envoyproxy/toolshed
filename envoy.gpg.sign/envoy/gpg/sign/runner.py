
import argparse
import pathlib
import re
import tempfile
from functools import cached_property
from typing import Optional, Type

from aio.run import runner

from envoy.base import utils
from envoy.gpg import identity

from .exceptions import SigningError
from .util import DirectorySigningUtil


SIGNING_KEY_PATH = "signing.key"


class PackageSigningRunner(runner.Runner):
    """For a given `package_type` and `path` this will run the relevant signing
    util for the packages they contain."""

    _signing_utils = ()

    @classmethod
    def register_util(
            cls,
            name: str,
            util: Type[DirectorySigningUtil]) -> None:
        """Register util for signing a package type."""
        cls._signing_utils = getattr(cls, "_signing_utils") + ((name, util),)

    @property
    def gen_key(self) -> bool:
        return self.args.gen_key

    @property
    def gnupg_home(self) -> Optional[pathlib.Path]:
        return (
            pathlib.Path(self.gnupg_tempdir.name)
            if self.gen_key
            else None)

    @cached_property
    def gnupg_tempdir(self) -> tempfile.TemporaryDirectory:
        return tempfile.TemporaryDirectory()

    @property
    def infiles(self) -> str:
        """Path to the packages directory."""
        return self.args.infiles

    @cached_property
    def maintainer(self) -> identity.GPGIdentity:
        """A representation of the maintainer with GPG capabilities."""
        return self.maintainer_class(
            self.maintainer_name,
            self.maintainer_email,
            self.log,
            gnupg_home=self.gnupg_home,
            gen_key=self.gen_key)

    @property
    def maintainer_class(self) -> Type[identity.GPGIdentity]:
        return identity.GPGIdentity

    @property
    def maintainer_email(self) -> str:
        """Email of the maintainer if set."""
        return self.args.maintainer_email

    @property
    def maintainer_name(self) -> str:
        """Name of the maintainer if set."""
        return self.args.maintainer_name

    @property
    def mappings(self) -> dict[str, str]:
        return dict(
            utils.tuple_pair(m)
            for m
            in (self.args.mapping or []))

    @property
    def outfile(self) -> str:
        return self.args.out

    @property
    def package_type(self) -> str:
        """Package type - eg deb/rpm"""
        return self.args.package_type

    @property
    def repack(self):
        return utils.repack(
            self.outfile,
            *self.infiles,
            mappings=self.mappings,
            matching=re.compile("^(?!^(dbg|utils)).*"),
            include=re.compile(
                f"{self.signing_key_path}"
                f"|{'|'.join(self.signing_utils)}"))

    @property
    def signing_key_path(self) -> str:
        return SIGNING_KEY_PATH

    @cached_property
    def signing_utils(self) -> dict:
        """Configured signing utils - eg `DebSigningUtil`, `RPMSigningUtil`"""
        return dict(getattr(self, "_signing_utils"))

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        super().add_arguments(parser)
        parser.add_argument(
            "infiles",
            nargs="+",
            help="Paths to the tarballs containing packages to sign")
        parser.add_argument(
            "--out",
            help="Path to save the signed packages as tar file")
        parser.add_argument(
            "--type",
            default="",
            choices=[c for c in self.signing_utils] + [""],
            help="Package type to sign")
        parser.add_argument(
            "--maintainer-name",
            default="",
            help=(
                "Maintainer name to match when searching for a GPG key "
                "to match with"))
        parser.add_argument(
            "--maintainer-email",
            default="",
            help=(
                "Maintainer email to match when searching for a GPG key "
                "to match with"))
        parser.add_argument(
            "--gen-key",
            action="store_true",
            help=(
                "If set, create the signing key (requires "
                "`--maintainer-name` and `--maintainer-email`) "))
        parser.add_argument(
            "-m", "--mapping",
            action="append")

    def add_key(self, path: pathlib.Path) -> None:
        path.joinpath(
            self.signing_key_path).write_text(self.maintainer.export_key())

    async def cleanup(self):
        if "gnupg_tempdir" in self.__dict__:
            self.gnupg_tempdir.cleanup()
            del self.__dict__["gnupg_tempdir"]

    def get_signing_util(self, path: pathlib.Path) -> DirectorySigningUtil:
        return self.signing_utils[path.name](path, self.maintainer, self.log)

    @runner.catches((identity.GPGError, SigningError))
    @runner.cleansup
    async def run(self) -> None:
        with self.repack as tmpdir:
            self.sign_all(tmpdir)
            self.add_key(tmpdir)
        self.log.success(f"Successfully signed packages: {self.outfile}")

    def sign(self, path: pathlib.Path) -> None:
        self.log.notice(
            f"Signing {path.name}s ({self.maintainer}) {str(path)}")
        util = self.get_signing_util(path)
        util.sign()

    def sign_all(self, path: pathlib.Path) -> None:
        for directory in path.glob("*"):
            if directory.name in self.signing_utils:
                self.sign(directory)
