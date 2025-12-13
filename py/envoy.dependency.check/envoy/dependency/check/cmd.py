
import sys

from .checker import DependencyChecker


def main(*args: str) -> int:
    return DependencyChecker(*args)()


def run() -> None:
    sys.exit(main(*sys.argv[1:]))


if __name__ == "__main__":
    run()
