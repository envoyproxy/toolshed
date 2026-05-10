
import sys
from typing import Optional

from .deb import DebRepoManager
from .runner import RepoBuildingRunner


DEPRECATION_NOTICE = (
    "DEPRECATED: envoy.distribution.repo is inactive "
    "and no longer maintained. Do not use.")


def _register_repo_types() -> None:
    RepoBuildingRunner.register_repo_type("deb", DebRepoManager)


def main(*args: str) -> Optional[int]:
    _register_repo_types()
    return RepoBuildingRunner(*args)()


def cmd():
    sys.stderr.write(f"{DEPRECATION_NOTICE}\n")
    sys.exit(main(*sys.argv[1:]))


if __name__ == "__main__":
    cmd()
