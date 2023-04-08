
import asyncio
import contextlib
import gzip
import inspect
import os
import textwrap
from typing import (
    Any, Awaitable, Callable,
    Iterable, Iterator, List, Optional, Sized, Type, Union)

from trycast import isassignable  # type:ignore

# condition needed due to https://github.com/bazelbuild/rules_python/issues/622
try:
    import orjson as json
except ImportError:
    import json  # type:ignore

from aio.core.functional import exceptions


def maybe_awaitable(result: Any) -> Awaitable:
    """Make anything awaitable.

    ```python

    async def async_fun():
        return "ASYNC FUN"

    >>> await maybe_awaitable("CABBAGE")
    'CABBAGE'
    >>> await maybe_awaitable(async_fun())
    'ASYNC FUN'

    ```
    """

    return (
        result
        if inspect.iscoroutine(result)
        else asyncio.sleep(0, result=result))


def maybe_coro(fun: Union[Callable, Awaitable]) -> Callable[..., Awaitable]:
    """Make any callable into a coroutine function.

    ```python

    def fun():
        return "FUN"

    async def async_fun():
        return "ASYNC FUN"

    >>> await maybe_coro(fun)()
    'FUN'
    >>> await maybe_coro(async_fun)()
    'ASYNC FUN'

    ```
    """

    async def async_wrapper(*args, **kwargs):
        called = fun(*args, **kwargs)
        return (
            await called
            if inspect.iscoroutinefunction(fun)
            else called)
    return async_wrapper


@contextlib.contextmanager
def nested(*contexts):
    with contextlib.ExitStack() as stack:
        yield [
            stack.enter_context(context)
            for context
            in contexts]


def junzip(data: bytes) -> Any:
    return json.loads(gzip.decompress(data))


def typed(tocast: Type, value: Any) -> Any:
    """Attempts to cast a value to a given type, TypeVar, or TypeDict.

    raises TypeError if cast value is `None`
    """
    if isassignable(value, tocast):
        return value
    raise exceptions.TypeCastingError(
        "Value has wrong type or shape for Type "
        f"{tocast}: "
        f"{textwrap.shorten(str(value), width=10, placeholder='...')}",
        value=value)


# TODO: add async versions of the `batch` utils
def batches(items: Iterable, batch_size: int) -> Iterator[List]:
    """Yield batches of items according to batch size."""
    batch = []
    for item in items:
        batch.append(item)
        if len(batch) >= batch_size:
            yield batch
            batch = []
    if batch:
        yield batch


def batch_jobs(
        jobs: Sized,
        max_batch_size: Optional[int] = None,
        min_batch_size: Optional[int] = None) -> Iterator[List]:
    """Batch jobs between processors, optionally setting a max batch size."""
    bad_jobs_type = (
        not isinstance(jobs, Iterable)
        or isinstance(jobs, (str, bytes)))
    if bad_jobs_type:
        raise exceptions.BatchedJobsError(
            f"Wrong type for `batch_jobs` ({type(jobs)}: {jobs}")
    proc_count = os.cpu_count() or 1
    batch_count = round(len(jobs) / proc_count)
    if max_batch_size:
        batch_count = min(batch_count, max_batch_size)
    if min_batch_size:
        batch_count = max(batch_count, min_batch_size)
    return batches(typed(Iterable, jobs), batch_size=batch_count)
