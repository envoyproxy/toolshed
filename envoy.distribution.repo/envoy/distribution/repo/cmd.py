
import sys
from typing import Optional

from .deb import DebRepoManager
from .runner import RepoBuildingRunner


def _register_repo_types() -> None:
    RepoBuildingRunner.register_repo_type("deb", DebRepoManager)


def main(*args: str) -> Optional[int]:
    _register_repo_types()
    return RepoBuildingRunner(*args)()


def cmd():
    sys.exit(main(*sys.argv[1:]))


if __name__ == "__main__":
    cmd()
