
from typing import (
    Any, AsyncGenerator, AsyncIterable, Awaitable, Callable,
    Iterator, Mapping, Type)

from aio.core.functional import exceptions
from .utils import maybe_coro, typed


async def async_iterator(
        iterable: AsyncGenerator | AsyncIterable,
        predicate: (
            Callable[[Any], bool]
            | Awaitable[bool]
            | None) = None,
        result: Callable[[Any], Any] | None = None) -> AsyncGenerator:
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
        gen: AsyncGenerator | AsyncIterable,
        filter: Callable | None = None,
        predicate: (
            Callable[[Any], bool]
            | Awaitable[bool]
            | None) = None,
        result: Callable[[Any], Any] | None = None) -> list:
    """Turn an async generator into a here and now list, with optional
    filter."""
    results = list()
    iterator = async_iterator(gen, predicate=predicate, result=result)
    async for item in iterator:
        results.append(item)
    return results


async def async_set(
        iterable: AsyncIterable,
        predicate: (
            Callable[[Any], bool]
            | Awaitable[bool]
            | None) = None,
        result: Callable[[Any], Any] | None = None) -> set:
    """Create a set from the results of an async generator."""
    results = set()
    iterator = async_iterator(iterable, predicate=predicate, result=result)
    async for item in iterator:
        results.add(item)
    return results


# TODO: use Mapping rather than Dict
SearchKey = str | int
CollectionQueryDict = dict[SearchKey, str]
CollectionResultDict = dict[str, Any]
SearchableCollection = Mapping[SearchKey, Any]
Indexable = Mapping[int, Any]


class _SearchableCollection(SearchableCollection):

    def __init__(self, collection: Mapping) -> None:
        self._collection = collection

    def __getitem__(self, k: SearchKey) -> Any:
        return self._collection.__getitem__(k)

    def __iter__(self) -> Iterator:
        return self._collection.__iter__()

    def __len__(self) -> int:
        return self._collection.__len__()


class CollectionQuery:

    def __init__(self, data: SearchableCollection) -> None:
        self.data = data

    def __call__(
            self,
            query: CollectionQueryDict) -> CollectionResultDict:
        return dict(self.iter_queries(query))

    def __getitem__(self, query: str | int) -> Any:
        return self.query(query)

    def iter_queries(
            self,
            queries: CollectionQueryDict) -> Iterator[tuple[str, Any]]:
        for k, v in queries.items():
            yield str(k), self.query(v)

    def query(self, query: SearchKey) -> Any:
        data = self.data
        for path in self.spliterator(query):
            data = self.traverse(query, data, path)
        return data

    def traverse(self, query: SearchKey, data: Any, path: SearchKey):
        if not isinstance(path, int):
            try:
                return self.traverse_mapping(data, path)
            except KeyError as e:
                raise exceptions.CollectionQueryError(
                    f"Unable to traverse mapping {path} in {query}: {e}")
        try:
            return self.traverse_indexable(data, path)
        except IndexError as e:
            raise exceptions.CollectionQueryError(
                f"Unable to traverse index {path} in {query}: {e}")

    def spliterator(self, query: SearchKey) -> Iterator[int | str]:
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
            data: dict[SearchKey, Any],
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
            data: Mapping) -> CollectionResultDict:
        # TODO: optimize retrieving from same paths
        return self.query_dict(data)

    def query_dict(self, data: SearchableCollection) -> CollectionResultDict:
        return self.query_class(_SearchableCollection(data))(self.query)

    @property
    def query_class(self) -> Type[CollectionQuery]:
        return CollectionQuery


def qdict(**query) -> QueryDict:
    return QueryDict(typed(CollectionQueryDict, query))
