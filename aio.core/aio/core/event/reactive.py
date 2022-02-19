
import asyncio
from concurrent import futures
from functools import cached_property
from typing import Optional

import abstracts


class IReactive(metaclass=abstracts.Interface):
    """Object that has a `loop`."""

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
        """Event loop.

        Does not expect an existing loop to be running if it is not
        passed a loop.
        """
        return self._loop or asyncio.get_event_loop()

    @cached_property
    def pool(self) -> futures.Executor:
        return self._pool or futures.ProcessPoolExecutor()
