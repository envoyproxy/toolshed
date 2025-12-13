
import sys

from .project_runner import ProjectRunner


def main(*args: str) -> int:
    return ProjectRunner(*args)()


def project_cmd():
    sys.exit(main(*sys.argv[1:]))


if __name__ == "__main__":
    project_cmd()
