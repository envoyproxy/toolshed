
import asyncio
from concurrent import futures
from functools import cached_property

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
    _loop: asyncio.AbstractEventLoop | None = None
    _pool: futures.Executor | None = None

    @cached_property
    def loop(self) -> asyncio.AbstractEventLoop:
        """Event loop.

        Returns the injected loop if one was passed; otherwise returns
        the existing event loop for this thread, creating and setting a
        new one if none exists.

        Does not expect an existing loop to be running.
        """
        if self._loop:
            return self._loop
        try:
            return asyncio.get_event_loop_policy().get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return loop

    @cached_property
    def pool(self) -> futures.Executor:
        return self._pool or futures.ProcessPoolExecutor()
