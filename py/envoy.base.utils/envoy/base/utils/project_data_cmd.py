
import sys

from .project_runner import ProjectDataRunner


def main(*args: str) -> int:
    return ProjectDataRunner(*args)()


def project_data_cmd():
    sys.exit(main(*sys.argv[1:]))


if __name__ == "__main__":
    project_data_cmd()
