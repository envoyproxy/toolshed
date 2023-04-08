
import sys

from .checker import Dependatool


def main(*args: str) -> int:
    return Dependatool(*args)()


def cmd():
    sys.exit(main(*sys.argv[1:]))


if __name__ == "__main__":
    cmd()
