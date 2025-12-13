
import sys

from .runner import ReportRunner


def main(*args: str) -> int | None:
    return ReportRunner(*args)()


def cmd():
    sys.exit(main(*sys.argv[1:]))


if __name__ == "__main__":
    cmd()
