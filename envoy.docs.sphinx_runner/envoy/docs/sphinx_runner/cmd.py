
import sys

from .runner import SphinxRunner


def main(*args: str) -> int:
    return SphinxRunner(*args).run()


def cmd():
    sys.exit(main(*sys.argv[1:]))


if __name__ == "__main__":
    cmd()
