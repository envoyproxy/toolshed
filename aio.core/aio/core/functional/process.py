
import asyncio
from concurrent import futures
from typing import AsyncIterator, Callable, Coroutine, Iterable, Optional

from aio.core import functional


async def async_map(
        fun: Callable,
        iterable: Iterable,
        fork: bool = False) -> AsyncIterator:
    """Asynchronously map synchronous function with an iterable, yielding
    results as available.

    By default a `ThreadPoolExecutor` will be used, setting `fork` to
    `True` will instead use a `ProcessPoolExecutor` to fork the function
    to separate processes.
    """
    executor = (
        futures.ProcessPoolExecutor
        if fork
        else futures.ThreadPoolExecutor)

    with executor() as pool:
        result_futures = list(map(lambda x: pool.submit(fun, x), iterable))
        for future in futures.as_completed(result_futures):
            yield future.result()


async def threaded(
        fun: Callable,
        *args,
        pool: Optional[futures.ThreadPoolExecutor] = None,
        stdout: Optional[Callable[..., Coroutine]] = None,
        stderr: Optional[Callable[..., Coroutine]] = None,
        both: Optional[Callable[..., Coroutine]] = None) -> asyncio.Future:

    if not any([stdout, stderr, both]):
        return await asyncio.get_running_loop().run_in_executor(
            pool,
            fun,
            *args)

    output = dict(stdout=stdout, stderr=stderr, both=both)
    async with functional.capturing(output) as buffer:
        return await asyncio.get_running_loop().run_in_executor(
            pool,
            functional.buffering,
            fun,
            buffer.get("stdout"),
            buffer.get("stderr"),
            *args)
