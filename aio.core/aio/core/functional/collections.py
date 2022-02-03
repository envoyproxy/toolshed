
from typing import (
    Any, AsyncGenerator, AsyncIterable, Awaitable, Callable,
    List, Optional, Set, Union)

from .utils import maybe_coro


async def async_iterator(
        iterable: AsyncIterable,
        predicate: Optional[
            Union[
                Callable[[Any], bool],
                Awaitable[bool]]] = None,
        result: Optional[Callable[[Any], Any]] = None) -> AsyncGenerator:
    """Iterate results of an async generator, yielding mutated results based on
    predicate."""
    result = maybe_coro(
        result
        or (lambda item: item))
    predicate_fun = (
        maybe_coro(predicate)
        if predicate
        else None)
    async for item in iterable:
        if not predicate_fun or await predicate_fun(item):
            yield await result(item)


async def async_list(
        iterable: AsyncIterable,
        predicate: Optional[
            Union[
                Callable[[Any], bool],
                Awaitable[bool]]] = None,
        result: Optional[Callable[[Any], Any]] = None) -> List:
    """Create a list from the results of an async generator."""
    results = list()
    iterator = async_iterator(iterable, predicate=predicate, result=result)
    async for item in iterator:
        results.append(item)
    return results


async def async_set(
        iterable: AsyncIterable,
        predicate: Optional[
            Union[
                Callable[[Any], bool],
                Awaitable[bool]]] = None,
        result: Optional[Callable[[Any], Any]] = None) -> Set:
    """Create a set from the results of an async generator."""
    results = set()
    iterator = async_iterator(iterable, predicate=predicate, result=result)
    async for item in iterator:
        results.add(item)
    return results
