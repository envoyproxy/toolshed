
import sys

from .checker import PackagesDistroChecker


def main(*args: str) -> int:
    return PackagesDistroChecker(*args)()


def cmd():
    sys.exit(main(*sys.argv[1:]))


if __name__ == "__main__":
    cmd()
