
from typing import (
    Any, AsyncIterable, Awaitable, Callable,
    List, Optional, Set, Union)

from .utils import maybe_coro


async def async_set(
        iterable: AsyncIterable,
        predicate: Optional[
            Union[
                Callable[[Any], bool],
                Awaitable[bool]]] = None,
        result: Optional[Callable[[Any], Any]] = None) -> Set:
    """Create a set from the results of an async generator."""
    results = set()
    result = maybe_coro(
        result
        or (lambda item: item))
    predicate_fun = (
        maybe_coro(predicate)
        if predicate
        else None)
    async for item in iterable:
        if not predicate_fun or await predicate_fun(item):
            results.add(await result(item))
    return results


async def async_list(
        iterable: AsyncIterable,
        predicate: Optional[
            Union[
                Callable[[Any], bool],
                Awaitable[bool]]] = None,
        result: Optional[Callable[[Any], Any]] = None) -> List:
    """Create a list from the results of an async generator."""
    results = list()
    result = maybe_coro(
        result
        or (lambda item: item))
    predicate_fun = (
        maybe_coro(predicate)
        if predicate
        else None)
    async for item in iterable:
        if not predicate_fun or await predicate_fun(item):
            results.append(await result(item))
    return results
