
import argparse

from typing import Any

import abstracts


class IProcessor(metaclass=abstracts.Interface):

    @abstracts.interfacemethod
    def __call__(self, *args):
        raise NotImplementedError


class IStdinStdoutProcessor(IProcessor, metaclass=abstracts.Interface):

    @abstracts.interfacemethod
    def __init__(self, processor, stdin=None, stdout=None, log=None):
        raise NotImplementedError


class IProcessProtocol(metaclass=abstracts.Interface):

    @classmethod
    @abstracts.interfacemethod
    def add_protocol_arguments(cls, parser: argparse.ArgumentParser) -> None:
        raise NotImplementedError

    @abstracts.interfacemethod
    def __init__(
            self,
            processor: IProcessor,
            args: argparse.Namespace) -> None:
        raise NotImplementedError

    @abstracts.interfacemethod
    async def __call__(self, request: Any) -> Any:
        raise NotImplementedError

    @abstracts.interfacemethod
    async def process(self, request: Any) -> Any:
        raise NotImplementedError
