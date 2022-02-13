
import asyncio
import contextlib
import gzip
import inspect
import textwrap
from typing import (
    Any, Awaitable, Callable, Coroutine, Union)

from trycast import trycast  # type:ignore

import orjson as json

from aio.core.functional import exceptions


def maybe_awaitable(result: Any) -> Coroutine:
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


# Due to patchy mypy support, `tocast` has to be an `object` for now.
# This should be more strictly typed once mypy has `TypeForm` support.
def typed(tocast: object, value: Any) -> Any:
    """Attempts to cast a value to a given type, TypeVar, or TypeDict.

    raises TypeError if cast value is `None`
    """

    if trycast(tocast, value) is not None:
        return value
    raise exceptions.TypeCastingError(
        "Value has wrong type or shape for Type "
        f"{tocast}: "
        f"{textwrap.shorten(str(value), width=10, placeholder='...')}")
