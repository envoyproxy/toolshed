
from functools import cached_property
from typing import Dict, Tuple, Type

from envoy.base.runner import AsyncRunner

from .command import AsyncCommand


class AsyncRunnerWithCommands(AsyncRunner):
    _commands: Tuple[Tuple[str, Type[AsyncCommand]], ...] = ()

    @classmethod
    def register_command(cls, name: str, command: Type[AsyncCommand]) -> None:
        """Register a repo type"""
        cls._commands = getattr(cls, "_commands") + ((name, command),)

    @cached_property
    def command(self) -> AsyncCommand:
        return self.commands[self.args.command](self)

    @cached_property
    def commands(self) -> Dict[str, Type[AsyncCommand]]:
        return {k: v for k, v in self._commands}

    async def run(self) -> None:
        await self.command.run()
