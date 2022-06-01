
import sys

from .jinja_env import JinjaEnvironment


def main(*args: str) -> int:
    return (
        0
        if not JinjaEnvironment.create(*args)
        else 1)


def jinja_env_cmd() -> None:
    sys.exit(main(*sys.argv[1:]))


if __name__ == "__main__":
    jinja_env_cmd()
