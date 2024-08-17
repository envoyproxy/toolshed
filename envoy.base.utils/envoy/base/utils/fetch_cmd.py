
import sys

from .fetch_runner import FetchRunner


def main(*args: str) -> int:
    return FetchRunner(*args)()


def fetch_cmd():
    sys.exit(main(*sys.argv[1:]))


if __name__ == "__main__":
    fetch_cmd()
