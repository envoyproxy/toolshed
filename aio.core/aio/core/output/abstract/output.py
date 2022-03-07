
import abc
import asyncio
import io
from functools import cached_property, partial
from typing import (
    Any, Callable, Coroutine, Dict, List, Optional, Type)

import janus

import abstracts

from aio import core
from aio.core import functional


DEATH_SENTINEL = object()


class ACapturedOutputs(metaclass=abstracts.Abstraction):
    """Wraps a list of captured outputs and allows you to
    print them, or filter them base on type."""

    def __init__(self, outputs, output_types=None, out_file=None):
        self._outputs = outputs
        self._output_types = output_types
        self.out_file = functional.maybe_coro(out_file or print)

    def __getitem__(self, type):
        return list(self.output_for(type))

    @property
    def output(self):
        return "\n".join(
            f"{result.type}: {str(result)}"
        for result in self._outputs)

    @cached_property
    def output_types(self):
        if self._output_types:
            return self._output_types
        return dict(
            stdout=sys.stdout,
            stderr=sys.stderr)

    async def drain(self, type=None):
        types = [type] if type else self.output_types.keys()
        for output_type in types:
            for output in self[output_type]:
                await self.out_file(
                    output,
                    file=self.output_types[output_type])

    def output_for(self, type):
        for result in self._outputs:
            if result.type == type:
                yield result


class ACapturedOutput(metaclass=abstracts.Abstraction):
    """Captured output of a given type, eg `stdout`, `stderr`"""

    def __init__(
            self,
            type: str,
            message: bytes,
            encoding: str = "utf-8") -> None:
        self.type = type
        self.message = message
        self.encoding = encoding

    def __str__(self) -> str:
        return self.message.decode(self.encoding).strip()


class AQueueIO(metaclass=abstracts.Abstraction):
    """An IO writer that writes items to a `janus.SyncQueue`."""

    def __init__(
            self,
            type: str,
            q: janus.SyncQueue,
            output: Callable) -> None:
        self.type = type
        self.q = q
        self._output = output

    @property
    def closed(self) -> bool:
        return self.q.closed

    def readable(self) -> bool:
        return False

    def seekable(self) -> bool:
        return False

    def write(self, msg: bytes) -> None:
        self.q.put(self._output(msg))

    def writable(self) -> bool:
        return True


class ABufferedOutputs(metaclass=abstracts.Abstraction):
    """Async contextmanager which queues messages wrapped (by default) as
    `CapturedOutput` objects for given output types and handlers.

    This allows output from a synchronous function to be yielded
    asynchronously in a thread-safe manner.
    """

    def __init__(
            self,
            handlers: Dict[str, Callable[..., Coroutine]],
            queue_class: Type[janus.Queue] = janus.Queue,
            output_class: Optional[Type[ACapturedOutput]] = None,
            io_class: Optional[Type[AQueueIO]] = None) -> None:
        self.handlers = handlers
        self._output_class = output_class
        self._io_class = io_class
        self._queue_class = queue_class

    async def __aenter__(self) -> "ABufferedOutputs":
        return self

    async def __aexit__(self, *exception) -> None:
        await self.stop_queues()
        await self.wait_for_tasks()
        await self.close_queues()

    def __getitem__(self, k: str) -> io.TextIOWrapper:
        return self.buffers[k]

    @cached_property
    def buffers(self) -> Dict[str, io.TextIOWrapper]:
        """Named `io` buffers."""
        return {
            buffer: self._io(buffer)
            for buffer
            in self.handlers}

    @property  # type:ignore
    @abstracts.interfacemethod
    def io_class(self) -> Type[AQueueIO]:
        """`io` queue class.`"""
        raise NotImplementedError

    @cached_property
    def loop(self) -> asyncio.AbstractEventLoop:
        """Event loop."""
        return asyncio.get_running_loop()

    @property  # type:ignore
    @abstracts.interfacemethod
    def output_class(self) -> Type[ACapturedOutput]:
        """Class to wrap output in."""
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def queue_class(self) -> Type[janus.Queue]:
        """Combined sync/async queue class."""
        return self._queue_class

    @cached_property
    def queues(self) -> Dict[str, janus.Queue[ACapturedOutput]]:
        """Queues for each output type."""
        return {
            buffer: self.queue_class()
            for buffer
            in self.handlers}

    @cached_property
    def tasks(self) -> List[asyncio.Task]:
        """Tasks listening for event to push to their queues."""
        return []

    async def close_queue(self, q: janus.Queue[ACapturedOutput]) -> None:
        """Close a sync/async queue."""
        q.close()
        await q.wait_closed()

    async def close_queues(self) -> None:
        """Close all queues."""
        await core.tasks.concurrent(
            self.close_queue(q)
            for q
            in self.queues.values())

    def get(self, k: str, default: Any = None) -> Any:
        """Get an output buffer by name."""
        return (
            self.buffers[k]
            if k in self.buffers
            else default)

    async def stop_queue(self, q: janus.AsyncQueue) -> None:
        """Stop a queue."""
        await q.put(DEATH_SENTINEL)

    async def stop_queues(self) -> None:
        """Stop all queues."""
        await core.tasks.concurrent(
            self.stop_queue(q.async_q)
            for q
            in self.queues.values())

    async def wait_for_tasks(self) -> None:
        """Wait for tasks to complete."""
        await core.tasks.concurrent(self.tasks)

    def _io(self, output_type: str) -> io.TextIOWrapper:
        """A `TextIO` object that wraps a `QueueIO`."""
        q = self.queues[output_type]
        handler = self.handlers[output_type]
        self.tasks.append(
            self.loop.create_task(
                self._reader(q.async_q, handler)))
        return io.TextIOWrapper(
            self.io_class(
                output_type,
                q.sync_q,
                partial(
                    self.output_class,
                    output_type)),
            # line_buffering=True,
            write_through=True)

    async def _reader(
            self,
            q: janus.AsyncQueue[ACapturedOutput],
            handler: Callable[..., Coroutine]) -> None:
        """Listen for and handle queue events."""
        while True:
            out = await q.get()
            q.task_done()
            if out is DEATH_SENTINEL:
                break
            await handler(out)
