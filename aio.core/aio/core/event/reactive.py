
import asyncio
from concurrent import futures
from functools import cached_property
from typing import Optional

import abstracts


class IReactive(metaclass=abstracts.Interface):

    @property  # type: ignore
    @abstracts.interfacemethod
    def loop(self) -> asyncio.AbstractEventLoop:
        """Event loop."""
        raise NotImplementedError

    @property  # type: ignore
    @abstracts.interfacemethod
    def pool(self) -> futures.Executor:
        """Processor pool."""
        raise NotImplementedError


class AReactive(IReactive, metaclass=abstracts.Abstraction):
    _loop: Optional[asyncio.AbstractEventLoop] = None
    _pool: Optional[futures.Executor] = None

    @cached_property
    def loop(self) -> asyncio.AbstractEventLoop:
        return self._loop or asyncio.get_running_loop()

    @cached_property
    def pool(self) -> futures.Executor:
        return self._pool or futures.ProcessPoolExecutor()
