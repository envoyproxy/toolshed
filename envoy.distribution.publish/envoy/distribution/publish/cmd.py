
import asyncio
import sys
from typing import Optional

from .runner import ReleaseRunner
from .command import (
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


# from memory_profiler import profile

# @profile
def main(*args: str) -> Optional[int]:
    _register_commands()
    runner = ReleaseRunner(*args)
    try:
        return asyncio.run(runner.run())
    except KeyboardInterrupt:
        runner.log.error("Keyboard exit")
        return 1


def cmd():
    sys.exit(main(*sys.argv[1:]))


if __name__ == "__main__":
    cmd()
