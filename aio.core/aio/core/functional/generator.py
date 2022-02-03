
from typing import (
    Any, AsyncIterable, AsyncIterator, Awaitable,
    Callable, Coroutine, Dict, Generator, Iterable, Optional, Union)

from aio.core import functional


class AwaitableGenerator:
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
            generator: AsyncIterable,
            collector: Callable[
                ...,
                Coroutine[
                    AsyncIterable,
                    None,
                    Iterable]] = None,
            iterator: Any = None,
            predicate: Optional[
                Union[
                    Callable[[Any], bool],
                    Awaitable[bool]]] = None,
            result: Optional[
                Callable[[Any], Any]] = None) -> None:
        self.generator = generator
        self.collector = collector or functional.async_list
        self.iterator = iterator or functional.async_iterator
        self.predicate = predicate
        self.result = result

    async def __aiter__(self) -> AsyncIterator:
        async for item in self.iterable:
            yield item

    def __await__(self) -> Generator:
        return self.awaitable.__await__()

    @property
    def awaitable(self) -> Awaitable:
        return self.collector(self.generator, **self.iter_kwargs)

    @property
    def iterable(self) -> AsyncIterator:
        return self.iterator(self.generator, **self.iter_kwargs)

    @property
    def iter_kwargs(self) -> Dict:
        return dict(
            predicate=self.predicate,
            result=self.result)
