
import sys

from .checker import PythonChecker


def main(*args: str) -> int:
    return PythonChecker(*args).run()


def cmd():
    sys.exit(main(*sys.argv[1:]))


if __name__ == "__main__":
    cmd()
