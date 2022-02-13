
from typing import (
    Any, AsyncGenerator, AsyncIterable, Awaitable, Callable,
    Dict, Iterator, List, Mapping, Optional, Set, Tuple, Type, Union)

from aio.core.functional import exceptions
from .utils import maybe_coro, typed


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


# TODO: use Mapping rather than Dict
SearchKey = Union[str, int]
CollectionQueryDict = Dict[SearchKey, str]
CollectionResultDict = Dict[str, Any]
Indexable = Mapping[int, Any]
SearchableCollection = Union[Indexable, Dict[str, Any]]


class CollectionQuery:

    def __init__(self, data: SearchableCollection) -> None:
        self.data = data

    def __call__(
            self,
            query: CollectionQueryDict) -> CollectionResultDict:
        return dict(self.iter_queries(query))

    def __getitem__(self, query: Union[str, int]) -> Any:
        return self.query(query)

    def iter_queries(
            self,
            queries: CollectionQueryDict) -> Iterator[Tuple[str, Any]]:
        for k, v in queries.items():
            yield str(k), self.query(v)

    def query(self, query: SearchKey) -> Any:
        data = self.data
        for path in self.spliterator(query):
            data = self.traverse(query, data, path)
        return data

    def traverse(self, query: SearchKey, data: Any, path: SearchKey):
        if isinstance(data, dict):
            try:
                return self.traverse_mapping(
                    typed(Dict[SearchKey, Any], data),
                    path)
            except (KeyError, exceptions.TypeCastingError) as e:
                raise exceptions.CollectionQueryError(
                    f"Unable to traverse mapping {path} in {query}: {e}")
        try:
            return self.traverse_indexable(
                typed(Indexable, data),
                typed(int, path))
        except (IndexError, exceptions.TypeCastingError) as e:
            raise exceptions.CollectionQueryError(
                f"Unable to traverse index {path} in {query}: {e}")

    def spliterator(self, query: SearchKey) -> Iterator[Union[int, str]]:
        if isinstance(query, int):
            yield query
            return
        for path in query.split("/"):
            try:
                yield int(path)
            except ValueError:
                yield path

    # these could potentially use `@overload` decorator, and may not be
    # necessary. Makes mypy happy.
    def traverse_mapping(
            self,
            data: Dict[SearchKey, Any],
            key: SearchKey) -> Any:
        return data[key]

    def traverse_indexable(
            self,
            data: Indexable,
            key: int) -> Any:
        return data[key]


class QueryDict:

    def __init__(self, query: CollectionQueryDict) -> None:
        self.query = query

    def __call__(
            self,
            data: Any) -> CollectionResultDict:
        # TODO: optimize retrieving from same paths
        return self.query_dict(typed(SearchableCollection, data))

    def query_dict(self, data: SearchableCollection) -> CollectionResultDict:
        return self.query_class(data)(self.query)

    @property
    def query_class(self) -> Type[CollectionQuery]:
        return CollectionQuery


def qdict(**query) -> QueryDict:
    return QueryDict(typed(CollectionQueryDict, query))
