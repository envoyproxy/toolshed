
import argparse
from functools import cached_property
from typing import Dict, Tuple, Type


class BaseCommand:

    def __init__(self, runner):
        self.runner = runner
        self.context = runner

    @property
    def args(self):
        return self.parser.parse_known_args(self.context.extra_args)[0]

    @property
    def extra_args(self):
        return self.parser.parse_known_args(self.context.extra_args)[1]

    @cached_property
    def parser(self) -> argparse.ArgumentParser:
        """Argparse parser"""
        parser = argparse.ArgumentParser(allow_abbrev=False)
        self.add_arguments(parser)
        return parser

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        """Override this method to add custom arguments to the arg parser"""
        pass


class Command(BaseCommand):

    def run(self):
        raise NotImplementedError


class BaseSubcommand(BaseCommand):

    def __init__(self, context):
        self.context = context

    @cached_property
    def runner(self):
        return self.context.runner


class Subcommand(BaseSubcommand):

    def run(self):
        raise NotImplementedError


class BaseCommandWithSubcommands(Command):
    _subcommands: Tuple = ()

    @classmethod
    def register_subcommand(
            cls,
            name: str,
            subcommand: Type[Subcommand]) -> None:
        """Register a repo type"""
        cls._subcommands = getattr(cls, "_subcommands") + ((name, subcommand),)

    @cached_property
    def subcommand(self) -> Subcommand:
        return self.subcommands[self.args.subcommand](self)

    @cached_property
    def subcommands(self) -> Dict[str, Type[Subcommand]]:
        return {k: v for k, v in self._subcommands}


class CommandWithSubcommands(BaseCommandWithSubcommands):
    _subcommands: Tuple[Tuple[str, Type[Subcommand]], ...] = ()

    def run(self) -> None:
        self.subcommand.run()


class AsyncCommand(BaseCommand):

    async def run(self):
        raise NotImplementedError


class AsyncSubcommand(BaseCommand):

    async def run(self):
        raise NotImplementedError


class AsyncCommandWithSubcommands(BaseCommandWithSubcommands):
    _subcommands: Tuple[Tuple[str, Type[AsyncSubcommand]], ...] = ()

    async def run(self) -> None:
        await self.subcommand.run()
