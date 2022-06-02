
import sys
from typing import Optional

from .data_env import DataEnvironment


def main(*args: str) -> Optional[int]:
    return DataEnvironment.create(*args)


def data_env_cmd() -> None:
    sys.exit(main(*sys.argv[1:]))


if __name__ == "__main__":
    data_env_cmd()
