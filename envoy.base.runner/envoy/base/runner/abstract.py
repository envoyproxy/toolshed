
import abc

from typing import Dict, Optional, Tuple, Type

import abstracts

from .runner import AsyncRunner

from envoy.abstract.command import AAsyncCommand


AsyncCommandDict = Dict[str, Type[AAsyncCommand]]


class AAsyncRunnerWithCommands(AsyncRunner, metaclass=abstracts.Abstraction):
    _commands: Tuple[Tuple[str, Type[AAsyncCommand]], ...] = ()

    @classmethod
    def register_command(cls, name: str, command: Type[AAsyncCommand]) -> None:
        """Register a repo type"""
        cls._commands = getattr(cls, "_commands") + ((name, command),)

    @property
    @abc.abstractmethod
    def command(self) -> AAsyncCommand:
        return self.commands[self.args.command](self)

    @property
    @abc.abstractmethod
    def commands(self) -> AsyncCommandDict:
        return {k: v for k, v in self._commands}

    @abc.abstractmethod
    async def run(self) -> Optional[int]:
        return await self.command.run()
