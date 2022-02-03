
import sys

from .runner import PackageSigningRunner
from .deb import DebSigningUtil
from .rpm import RPMSigningUtil


def _register_utils() -> None:
    PackageSigningRunner.register_util("deb", DebSigningUtil)
    PackageSigningRunner.register_util("rpm", RPMSigningUtil)


def main(*args) -> int:
    _register_utils()
    return PackageSigningRunner(*args)()


def cmd():
    sys.exit(main(*sys.argv[1:]))


if __name__ == "__main__":
    cmd()
