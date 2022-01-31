
from concurrent import futures
from typing import AsyncIterator, Callable, Iterable


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
