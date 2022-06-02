
import sys
from typing import Optional

from .jinja_env import JinjaEnvironment


def main(*args: str) -> Optional[int]:
    return JinjaEnvironment.create(*args)


def jinja_env_cmd() -> None:
    sys.exit(main(*sys.argv[1:]))


if __name__ == "__main__":
    jinja_env_cmd()
