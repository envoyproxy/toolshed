import asyncio
import inspect
import os
import types
from functools import cached_property
from typing import (
    Any, AsyncIterable, AsyncIterator, Awaitable, Callable,
    Iterable, Iterator, List,
    Optional, Union)

from aio.core.functional import async_property, AwaitableGenerator

from .exceptions import (
    ConcurrentError, ConcurrentExecutionError, ConcurrentIteratorError)


_sentinel = object()


class Concurrent:
    """This utility provides very similar functionality to
    `asyncio.as_completed` in that it runs coroutines in concurrent, yielding
    the results as they are available.

    There are a couple of differences:

    - `coros` can be any `iterables` including sync/async `generators`
    - `limit` can be supplied to specify the maximum number of concurrent tasks

    Setting `limit` to `-1` will make all tasks run in concurrent.

    The default is `number of cores + 4` to a maximum of `32`.

    For network tasks it might make sense to set the concurrency `limit` lower
    than the default, if, for example, opening many concurrent connections will
    trigger rate-limiting or soak bandwidth.

    If an error is raised while trying to iterate the provided coroutines, the
    error is wrapped in an `ConcurrentIteratorError` and is raised immediately.

    In this case, no further handling occurs, and `yield_exceptions` has no
    effect.

    Any errors raised while trying to create or run tasks are wrapped in
    `ConcurrentError`.

    Any errors raised during task execution are wrapped in
    `ConcurrentExecutionError`.

    If you specify `yield_exceptions` as `True` then the wrapped errors will be
    yielded in the results.

    If `yield_exceptions` is False (the default), then the wrapped error will
    be raised immediately.

    If you use any kind of `Generator` or `AsyncGenerator` to produce the
    awaitables, and `yield_exceptions` is `False`, in the event that an error
    occurs, it is your responsibility to `close` remaining awaitables that you
    might have created but which have not already been fired.

    This utility is mostly useful for concurrentizing io-bound (as opposed to
    cpu-bound) tasks.

    Example usage:

    ```
    import random

    from tools.base import aio

    async def task_to_run(i):
        print(f"{i} starting")
        wait = random.random() * 10
        await asyncio.sleep(wait)
        return i, wait

    async def run(coros):
        async for (i, wait) in aio.concurrent(coros, limit=3):
            print(f"{i} waited {wait}")

    def provider():
        for i in range(0, 10):
            yield task_to_run(i)

    asyncio.run(run(provider()))
    ```
    """

    def __init__(
            self,
            coros: Union[
                types.AsyncGeneratorType,
                AsyncIterable[Awaitable],
                AsyncIterator[Awaitable],
                types.GeneratorType,
                Iterator[Awaitable],
                Iterable[Awaitable]],
            yield_exceptions: Optional[bool] = False,
            limit: Optional[int] = None):
        self._coros = coros
        self._limit = limit
        self._running: List[asyncio.Task] = []
        self.yield_exceptions = yield_exceptions

    def __aiter__(self) -> AsyncIterator:
        """Start a coroutine task to process the submit queue, and return an
        async generator to deliver results back as they arrive."""
        self.submit_task = asyncio.create_task(self.submit())
        return self.output()

    @property
    def active(self) -> bool:
        """Checks whether the iterator is active, either because it hasn't
        finished submitting or because there are still tasks running."""
        return self.submitting or self.running

    @property
    def closed(self) -> bool:
        """If an unhandled error occurs, the generator is closed and no further
        processing should happen."""
        return self.closing_lock.locked()

    @cached_property
    def closing_lock(self) -> asyncio.Lock:
        """Flag to indicate whether the generator has been closed."""
        return asyncio.Lock()

    @cached_property
    def consumes_async(self) -> bool:
        """Provided coros iterable is some kind of async provider."""
        return isinstance(
            self._coros,
            (types.AsyncGeneratorType, AsyncIterator, AsyncIterable))

    @cached_property
    def consumes_generator(self) -> bool:
        """Provided coros iterable is some kind of generator."""
        return isinstance(
            self._coros,
            (types.AsyncGeneratorType, types.GeneratorType))

    @async_property
    async def coros(self) -> AsyncIterator[
            Union[ConcurrentIteratorError, Awaitable]]:
        """An async iterator of the provided coroutines."""
        coros = self.iter_coros()
        try:
            async for coro in coros:
                yield coro
        except GeneratorExit:
            # If we exit before we finish generating we land here (ie error was
            # raised). In this case we need to tell the (possibly) async
            # generating provider to also close.
            try:
                await coros.aclose()  # type:ignore
            finally:
                # Suppress errors closing the provider generator
                # This can raise a further `GeneratorExit` but it will stop
                # providing.
                return

    @property
    def default_limit(self) -> int:
        """Default is to use cpu+4 to a max of 32 coroutines."""
        # This reflects the default for asyncio's `ThreadPoolExecutor`, this is
        # a fairly arbitrary number to use, but it seems like a reasonable
        # default.
        return min(32, (os.cpu_count() or 0) + 4)

    @cached_property
    def limit(self) -> int:
        """The limit for concurrent coroutines."""
        return self._limit or self.default_limit

    @cached_property
    def nolimit(self) -> bool:
        """Flag indicating no limit to concurrency."""
        return self.limit == -1

    @cached_property
    def out(self) -> asyncio.Queue:
        """Queue of results to yield back."""
        return asyncio.Queue()

    @property
    def running(self) -> bool:
        """Flag to indicate whether any tasks are running."""
        return not self.running_queue.empty()

    @cached_property
    def running_queue(self) -> asyncio.Queue:
        """Queue which is incremented/decremented as tasks begin/end.

        This is for tracking when there are no longer any tasks running.

        A queue is used here as opposed to other synchronization primitives, as
        it allows us to get the size and emptiness.

        The queue values are `None`.
        """
        return asyncio.Queue()

    @cached_property
    def running_tasks(self) -> List[asyncio.Task]:
        """Currently running asyncio tasks."""
        return self._running

    @cached_property
    def sem(self) -> asyncio.Semaphore:
        """A sem lock to limit the number of concurrent tasks."""
        return asyncio.Semaphore(self.limit)

    @cached_property
    def submission_lock(self) -> asyncio.Lock:
        """Submission lock to indicate when submission is complete."""
        return asyncio.Lock()

    @property
    def submitting(self) -> bool:
        """Flag to indicate whether we are still submitting coroutines."""
        return self.submission_lock.locked()

    async def cancel(self) -> None:
        """Stop the submission queue, cancel running tasks, close pending
        coroutines.

        This is triggered when an unhandled error occurs and the queue
        should stop processing and bail.
        """
        # Kitchen is closed
        await self.close()

        # No more waiting
        if not self.nolimit:
            self.sem.release()

        # Cancel tasks
        await self.cancel_tasks()

        # Close pending coroutines
        await self.close_coros()

        # let the submission queue die
        await self.submit_task

    async def cancel_tasks(self) -> None:
        """Cancel any running tasks."""

        for running in self.running_tasks:
            running.cancel()
            try:
                await running
            finally:
                # ignore errors, we are dying anyway
                continue

    async def close(self) -> None:
        """Close the generator, prevent any further processing."""
        if not self.closed:
            await self.closing_lock.acquire()

    async def close_coros(self) -> None:
        """Close provided coroutines (unless the provided coros is a
        generator)"""
        if self.consumes_generator:
            # If we have a generator, dont blow/create/wait upon any more items
            return

        async for coro in self.iter_coros():
            try:
                # this could be an `aio.ConcurrentError` and not have a
                # `close` method, but as we are asking for forgiveness anyway,
                # no point in looking before we leap.
                coro.close()  # type:ignore
            finally:
                # ignore errors, we are dying anyway
                continue

    async def create_task(self, coro: Awaitable) -> None:
        """Create an asyncio task from the coroutine, and remember it."""
        task = asyncio.create_task(self.task(coro))
        self.remember_task(task)
        self.running_queue.put_nowait(None)

    async def exit_on_completion(self) -> None:
        """Send the exit signal to the output queue."""
        if not self.active and not self.closed:
            await self.out.put(_sentinel)

    def forget_task(self, task: asyncio.Task) -> None:
        """Task?

        what task?
        """
        if self.closed:
            # If we are closing, don't remove, as this has been triggered
            # by cancellation.
            return
        self.running_tasks.remove(task)

    async def iter_coros(self) -> AsyncIterator[
            Union[ConcurrentIteratorError, Awaitable]]:
        """Iterate provided coros either synchronously or asynchronously,
        yielding the awaitables asynchoronously."""
        try:
            if self.consumes_async:
                async for coro in self._coros:  # type:ignore
                    yield coro
            else:
                for coro in self._coros:  # type:ignore
                    yield coro
        except BaseException as e:
            # Catch all errors iterating (other errors are caught elsewhere)
            # If iterating raises, wrap the error and send it to `submit` and
            # and `output` to close the queues.
            yield ConcurrentIteratorError(e)

    async def on_task_complete(
            self,
            result: Any,
            decrement: Optional[bool] = True) -> None:
        """Output the result, release the sem lock, decrement the running
        count, and notify output queue if complete."""
        if self.closed:
            # Results can come back after the queue has closed as they are
            # cancelled.
            # In that case, nothing further to do.
            return

        # Give result to output
        await self.out.put(result)

        if not self.nolimit:
            # Release the sem.lock
            self.sem.release()
        if decrement:
            # Decrement the running_queue if it was incremented
            self.running_queue.get_nowait()
        # Exit if nothing left to do
        await self.exit_on_completion()

    async def output(self) -> AsyncIterator:
        """Asynchronously yield results as they become available."""
        while True:
            # Wait for some output
            if (result := await self.out.get()) is _sentinel:
                # All done!
                await self.close()
                break
            elif error := self.raisable(result):
                # Raise an error and bail!
                await self.cancel()
                raise error
            yield result

    def raisable(self, result: Any) -> Optional[Exception]:
        """Check a result type and whether it should raise and return mangled
        error to ensure traceback from wrapped error."""
        should_error = (
            isinstance(result, ConcurrentIteratorError)
            or (isinstance(result, ConcurrentError)
                and not self.yield_exceptions))
        if not should_error:
            return None
        return (
            type(result)(
                type(result.args[0])(
                    str(result.args[0].__cause__),
                    *result.args[0].args[1:]))
            if (hasattr(result.args[0], "__cause__")
                and result.args[0].__cause__)
            else result)

    async def ready(self) -> bool:
        """Wait for the sem.lock and indicate availability in the submission
        queue."""
        if self.closed:
            return False
        if not self.nolimit:
            await self.sem.acquire()
            # We check before and after acquiring the sem.lock to see whether
            # we are `closed` as these events can be separated in
            # time/procedure.
            if self.closed:
                return False
        return True

    def remember_task(self, task: asyncio.Task) -> None:
        """Remember a scheduled asyncio task, in case it needs to be
        cancelled."""
        self.running_tasks.append(task)
        task.add_done_callback(self.forget_task)

    async def submit(self) -> None:
        """Process the iterator of coroutines as a submission queue."""
        await self.submission_lock.acquire()
        async for coro in self.coros:
            if isinstance(coro, ConcurrentIteratorError):
                # Iteration error, exit now
                await self.out.put(coro)
                break
            if not await self.ready():
                # Queue is closing, get out of here
                try:
                    # Ensure the last coro to be produced/generated is closed,
                    # as it will not be scheduled as a task, and in the case
                    # of generators it wont be closed any other way.
                    coro.close()
                finally:
                    # ignore all coro closing errors, we are dying
                    break
            # Check the supplied coro is awaitable
            try:
                self.validate_coro(coro)
            except ConcurrentError as e:
                await self.on_task_complete(e, decrement=False)
                continue
            # All good, create a task
            await self.create_task(coro)
        self.submission_lock.release()
        # If cleanup of the submission queue has taken longer than processing
        # we need to manually close
        await self.exit_on_completion()

    async def task(self, coro: Awaitable) -> None:
        """Task wrapper to catch/wrap errors and output awaited results."""
        try:
            result = await coro
        except BaseException as e:
            result = ConcurrentExecutionError(e)
        finally:
            await self.on_task_complete(result)

    def validate_coro(self, coro: Awaitable) -> None:
        """Validate that a provided coroutine is actually awaitable."""

        if not inspect.isawaitable(coro):
            raise ConcurrentError(
                f"Provided input was not a coroutine: {coro}")

        # TODO(phlax): debug this further and remove ignore.
        spent = (
            not asyncio.isfuture(coro)
            and (inspect.getcoroutinestate(coro)  # type:ignore
                 != inspect.CORO_CREATED))

        if spent:
            raise ConcurrentError(
                f"Provided coroutine has already been fired: {coro}")


def concurrent(*args, **kwargs) -> AwaitableGenerator:
    collector = kwargs.pop("collector", None)
    iterator = kwargs.pop("iterator", None)
    predicate = kwargs.pop("predicate", None)
    result = kwargs.pop("result", None)
    return AwaitableGenerator(
        Concurrent(*args, **kwargs),
        collector=collector,
        iterator=iterator,
        predicate=predicate,
        result=result)


async def inflate(
        iterable: Iterable,
        cb: Callable[[Any], Iterable[Awaitable]],
        yield_exceptions: Optional[bool] = None,
        limit: Optional[int] = None) -> AsyncIterable[Any]:
    """Inflate async data for an iterable of objects.

    The provided callback function should return an iterable of awaitables.

    For example, given a sequence of objects with an `id` property and cached
    async properties of `foo` and `bar`, this function can be used to preload
    the `foo` and `bar` properties for all the objects concurrently:

    ```python

    objects = inflate(
        inflatables,
        lambda o: (
            o.foo,
            o.bar))
    async for obj in objects:
        self.log.debug(f"Preloaded object: {obj.id}")
    ```
    """
    things = concurrent(
        (asyncio.gather(
            asyncio.sleep(0, result=thing),
            *cb(thing),
            return_exceptions=True)
         for thing
         in iterable),
        limit=limit,
        yield_exceptions=yield_exceptions)
    async for thing in things:
        if isinstance(thing[1], Exception):
            # TODO: test this further, and perhaps respect `yield_exceptions`
            raise thing[1]
        yield thing[0]
