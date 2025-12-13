
from typing import (
    Any, AsyncIterable, AsyncIterator, Awaitable,
    Callable, cast, Generator, TypeVar)

from aio.core import functional


T = TypeVar('T')
C = TypeVar('C', bound=Awaitable)


class AwaitableGenerator(Awaitable[C], AsyncIterable[T]):
    """Wrap an asynchronous generator as optionally awaitable.

    For example, you may have a low level async function that generates
    results, but where in some cases you want to just wait for the gathered
    results.

    The 2 methods of handling results show belown are functionally equivalent,
    except that in the second example all results are generated before
    iteration begins.

    ```python

    async def some_generator():
        for x in range(0, 5):
            yield x

    async for result in AwaitableGenerator(some_generator()):
        do_something_with(result)

    for result in await AwaitableGenerator(some_generator()):
        do_something_with(result)

    ```

    By default results will be collected into a `list`, using the
    `async_list` function. You can specify a custom collector as
    an argument to the constructor.

    The generator can be called with `predicate` and `result`, which
    are optionally async callables the results of which determine
    whether to include a result and how to yield/return it respectively.

    These args are passed to the collector function when instances of
    this class are awaited.
    """

    def __init__(
            self,
            generator: AsyncIterable[T],
            collector: Callable[..., Awaitable[C]] | None = None,
            iterator: Any = None,
            predicate: Callable[[T], bool] | Awaitable[bool] | None = None,
            result: Callable[[T], Any] | None = None) -> None:
        self.generator = generator
        self.collector = collector or functional.async_list
        self.iterator = iterator or functional.async_iterator
        self.predicate = predicate
        self.result = result

    async def __aiter__(self) -> AsyncIterator[T]:
        async for item in self.iterable:
            yield item

    def __await__(self) -> Generator[Any, None, C]:
        return self.awaitable.__await__()

    @property
    def awaitable(self) -> Awaitable[C]:
        result = self.collector(self.generator, **self.iter_kwargs)
        return cast(Awaitable[C], result)

    @property
    def iterable(self) -> AsyncIterator[T]:
        return self.iterator(self.generator, **self.iter_kwargs)

    @property
    def iter_kwargs(self) -> dict:
        return dict(
            predicate=self.predicate,
            result=self.result)
