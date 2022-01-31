
import asyncio
import inspect
from typing import Any, Awaitable, Callable, Coroutine, Union


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
