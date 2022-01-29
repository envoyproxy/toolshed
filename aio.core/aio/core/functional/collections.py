
from typing import Any, AsyncIterable, Callable, List, Optional, Set


async def async_set(
        iterable: AsyncIterable,
        predicate: Optional[Callable[[Any], bool]] = None,
        result: Optional[Callable[[Any], Any]] = None) -> Set:
    """Create a set from the results of an async generator."""
    results = set()
    result = result or (lambda path: path)
    async for item in iterable:
        if not predicate or predicate(item):
            results.add(result(item))
    return results


async def async_list(
        iterable: AsyncIterable,
        predicate: Optional[Callable[[Any], bool]] = None,
        result: Optional[Callable[[Any], Any]] = None) -> List:
    """Create a list from the results of an async generator."""
    results = list()
    result = result or (lambda path: path)
    async for item in iterable:
        if not predicate or predicate(item):
            results.append(result(item))
    return results
