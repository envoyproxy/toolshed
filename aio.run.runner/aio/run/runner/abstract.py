
import abc
import argparse
from typing import Dict, List, Optional, Tuple, Type

import abstracts

from .runner import Runner


class ICommand(metaclass=abstracts.Interface):

    @abstracts.interfacemethod
    async def run(self) -> Optional[int]:
        raise NotImplementedError


class ACommand(ICommand, metaclass=abstracts.Abstraction):

    def __init__(self, context):
        # TODO: add hint for context (IExtraArgs ?)
        self.context = context

    @property
    def args(self) -> argparse.Namespace:
        return self.parser.parse_known_args(self.context.extra_args)[0]

    @property
    def extra_args(self) -> List[str]:
        return self.parser.parse_known_args(self.context.extra_args)[1]

    @property
    @abc.abstractmethod
    def parser(self) -> argparse.ArgumentParser:
        """Argparse parser."""
        parser = argparse.ArgumentParser(allow_abbrev=False)
        self.add_arguments(parser)
        return parser

    @abstracts.interfacemethod
    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        """Override this method to add custom arguments to the arg parser."""
        raise NotImplementedError


CommandDict = Dict[str, Type[ACommand]]


class ARunnerWithCommands(Runner, metaclass=abstracts.Abstraction):
    _commands: Tuple[Tuple[str, Type[ACommand]], ...] = ()

    @classmethod
    def register_command(cls, name: str, command: Type[ACommand]) -> None:
        """Register a repo type."""
        cls._commands = getattr(cls, "_commands") + ((name, command),)

    @property
    @abc.abstractmethod
    def command(self) -> ACommand:
        return self.commands[self.args.command](self)

    @property
    @abc.abstractmethod
    def commands(self) -> CommandDict:
        return {k: v for k, v in self._commands}

    @abc.abstractmethod
    async def run(self) -> Optional[int]:
        return await self.command.run()
