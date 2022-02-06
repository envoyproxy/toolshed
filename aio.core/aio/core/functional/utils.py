
import asyncio
import contextlib
import inspect
import io
from typing import (
    Any, Awaitable, Callable, Coroutine,
    Iterator, List, Optional, Union)

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


@contextlib.contextmanager
def buffered(
        stdout: list = None,
        stderr: list = None,
        mangle: Optional[Callable[[list], list]] = None) -> Iterator[None]:
    """Captures stdout and stderr and feeds lines to supplied lists."""

    mangle = mangle or (lambda lines: lines)

    if stdout is None and stderr is None:
        raise exceptions.BufferUtilError(
            "You must specify stdout and/or stderr")

    contexts: List[
        Union[
            contextlib.redirect_stderr[io.TextIOWrapper],
            contextlib.redirect_stdout[io.TextIOWrapper]]] = []

    if stdout is not None:
        _stdout = io.TextIOWrapper(io.BytesIO())
        contexts.append(contextlib.redirect_stdout(_stdout))
    if stderr is not None:
        _stderr = io.TextIOWrapper(io.BytesIO())
        contexts.append(contextlib.redirect_stderr(_stderr))

    with nested(*contexts):
        yield

    if stdout is not None:
        _stdout.seek(0)
        stdout.extend(mangle(_stdout.read().strip().split("\n")))
    if stderr is not None:
        _stderr.seek(0)
        stderr.extend(mangle(_stderr.read().strip().split("\n")))
