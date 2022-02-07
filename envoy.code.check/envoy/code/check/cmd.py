
import sys

from .checker import CodeChecker


def main(*args: str) -> int:
    return CodeChecker(*args)()


def run() -> None:
    sys.exit(main(*sys.argv[1:]))


if __name__ == "__main__":
    run()
