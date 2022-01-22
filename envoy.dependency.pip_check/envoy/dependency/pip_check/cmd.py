
import sys

from .checker import PipChecker


def main(*args: str) -> int:
    return PipChecker(*args)()


def cmd():
    sys.exit(main(*sys.argv[1:]))


if __name__ == "__main__":
    cmd()
