
import sys
from typing import Optional

from .worker import BazelWorker


def main(*args: str) -> Optional[int]:
    return BazelWorker(*args)()


def worker_cmd() -> None:
    sys.exit(main(*sys.argv[1:]))


if __name__ == "__main__":
    worker_cmd()
