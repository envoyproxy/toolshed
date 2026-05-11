
import sys

from .runner import ReleaseRunner
from .commands import (
    AssetsCommand,
    CreateCommand,
    DeleteCommand,
    FetchCommand,
    InfoCommand,
    ListCommand,
    PushCommand)


def _register_commands():
    ReleaseRunner.register_command("list", ListCommand)
    ReleaseRunner.register_command("info", InfoCommand)
    ReleaseRunner.register_command("assets", AssetsCommand)
    ReleaseRunner.register_command("create", CreateCommand)
    ReleaseRunner.register_command("delete", DeleteCommand)
    ReleaseRunner.register_command("push", PushCommand)
    ReleaseRunner.register_command("fetch", FetchCommand)


def main(*args: str) -> int | None:
    _register_commands()
    result = ReleaseRunner(*args)()
    return result


def cmd():
    sys.exit(main(*sys.argv[1:]))


if __name__ == "__main__":
    cmd()
