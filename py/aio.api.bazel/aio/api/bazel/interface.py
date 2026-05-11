
import sys
from collections.abc import Awaitable, Callable
from typing import Any, TextIO

import abstracts

from aio.core import pipe


class IBazelProcessProtocol(
        pipe.IProcessProtocol,
        metaclass=abstracts.Interface):

    @abstracts.interfacemethod
    async def process(self, request: Any) -> Any:
        """Process incoming items."""
        raise NotImplementedError


class IBazelWorker(metaclass=abstracts.Interface):

    @property  # type:ignore
    @abstracts.interfacemethod
    def processor_class(self) -> type["IBazelWorkerProcessor"]:
        raise NotImplementedError

    @property  # type:ignore
    @abstracts.interfacemethod
    def protocol_class(self) -> type["IBazelProcessProtocol"]:
        raise NotImplementedError


class IBazelWorkerProcessor(
        pipe.IStdinStdoutProcessor,
        metaclass=abstracts.Interface):

    @abstracts.interfacemethod
    def __init__(
            self,
            protocol: Callable[
                ["IBazelWorkerProcessor"],
                Awaitable[IBazelProcessProtocol]],
            stdin: TextIO = sys.stdin,
            stdout: TextIO = sys.stdout,
            log: Callable[[str], None] | None = None) -> None:
        raise NotImplementedError

    @abstracts.interfacemethod
    def __call__(self, *args) -> Any:
        raise NotImplementedError
