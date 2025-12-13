
import sys

from .parallel_runner import ParallelRunner


def main(*args: str) -> int:
    return ParallelRunner(*args)()


def parallel_cmd():
    sys.exit(main(*sys.argv[1:]))


if __name__ == "__main__":
    parallel_cmd()
