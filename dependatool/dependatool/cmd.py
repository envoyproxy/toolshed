
import sys

from .checker import DependatoolChecker


def main(*args: str) -> int:
    return DependatoolChecker(*args)()


def cmd():
    sys.exit(main(*sys.argv[1:]))


if __name__ == "__main__":
    cmd()
