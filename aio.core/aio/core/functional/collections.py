
from typing import (
    Any, AsyncGenerator, AsyncIterable, Awaitable, Callable,
    Dict, Iterator, List, Optional, Set, Tuple, Type, Union)

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


class DictQuery:

    def __init__(self, data: Dict) -> None:
        self.data = data

    def __call__(
            self,
            query: Dict[str, str]) -> Dict[str, Any]:
        return dict(self.iter_queries(query))

    def __getitem__(self, query: str) -> Any:
        return self.query(query)

    def iter_queries(self, query: Dict[str, str]) -> Iterator[Tuple[str, Any]]:
        for k, v in query.items():
            yield k, self.query(v)

    def query(self, query: str) -> Any:
        data = self.data
        for path in self.spliterator(query):
            data = data[path]
        return data

    def spliterator(self, query: str) -> Iterator[Union[int, str]]:
        for path in query.split("/"):
            try:
                yield int(path)
            except ValueError:
                yield path


class QueryDict:

    def __init__(self, query: Dict) -> None:
        self.query = query

    def __call__(
            self,
            data: Dict[str, Any]) -> Dict[str, Any]:
        # TODO: optimize retrieving from same paths
        return self.query_dict(data)

    def query_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return self.query_class(data)(self.query)

    @property
    def query_class(self) -> Type[DictQuery]:
        return DictQuery


def qdict(**query: Dict) -> QueryDict:
    return QueryDict(query)
