
import abc
import argparse
from typing import List, Optional

import abstracts


class ABaseCommand(metaclass=abstracts.Abstraction):

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


class ICommand(metaclass=abstracts.Interface):

    @abstracts.interfacemethod
    def run(self) -> Optional[int]:
        raise NotImplementedError


class IAsyncCommand(metaclass=abstracts.Interface):

    @abstracts.interfacemethod
    async def run(self) -> Optional[int]:
        raise NotImplementedError


class ACommand(
        ICommand, ABaseCommand, metaclass=abstracts.Abstraction):
    pass


class AAsyncCommand(
        IAsyncCommand, ABaseCommand, metaclass=abstracts.Abstraction):
    pass
