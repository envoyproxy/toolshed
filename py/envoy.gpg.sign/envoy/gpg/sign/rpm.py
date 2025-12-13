
import pathlib
from functools import cached_property
from typing import Type, Union

from .exceptions import SigningError
from .util import DirectorySigningUtil


class RPMMacro:
    """`.rpmmacros` configuration for rpmsign."""

    _macro_filename = ".rpmmacros"

    def __init__(
            self,
            home: Union[pathlib.Path, str],
            overwrite: bool = False, **kwargs):
        self._home = home
        self.overwrite = bool(overwrite)
        self.kwargs = kwargs

    @property
    def home(self) -> pathlib.Path:
        return pathlib.Path(self._home)

    @property
    def path(self) -> pathlib.Path:
        return self.home.joinpath(self._macro_filename)

    @property
    def macro(self) -> str:
        macro = self.template
        for k, v in self.kwargs.items():
            macro = macro.replace(f"__{k.upper()}__", str(v))
        return macro

    @property
    def template(self) -> str:
        return pathlib.Path(
            __file__).parent.joinpath(
                "rpm_macro.tmpl").read_text()

    def write(self) -> None:
        if not self.overwrite and self.path.exists():
            return
        self.path.write_text(self.macro)


class RPMSigningUtil(DirectorySigningUtil):
    """Sign all RPM packages in a given directory."""

    command_name = "rpmsign"
    ext = "rpm"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setup()

    @cached_property
    def command(self) -> str:
        gpg2_available = (
            self.maintainer.gpg_bin
            and self.maintainer.gpg_bin.name == "gpg2")
        if not gpg2_available:
            raise SigningError("GPG2 is required to sign RPM packages")
        return super().command

    @cached_property
    def command_args(self) -> tuple:
        return ("--key-id", self.maintainer.fingerprint, "--addsign")

    @property
    def rpmmacro(self) -> Type[RPMMacro]:
        return RPMMacro

    def setup(self) -> None:
        """Create the .rpmmacros file if it doesn't exist."""
        self.rpmmacro(
            self.maintainer.home,
            maintainer=self.maintainer.name,
            gpg_bin=self.maintainer.gpg_bin,
            gpg_config=self.maintainer.gnupg_home).write()

    def sign_pkg(self, pkg_file: pathlib.Path) -> None:
        pkg_file.chmod(0o755)
        super().sign_pkg(pkg_file)
