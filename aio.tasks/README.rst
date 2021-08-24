
aio.tasks
=========

Utils for managing concurrent asyncio tasks.

You can use the ``concurrent`` async generator to run asyncio tasks
concurrently.

It works much like ``asyncio.as_available``, but with a couple of differences.

- ``coros`` can be any ``iterables`` including sync/async ``generators``
- ``limit`` can be supplied to specify the maximum number of concurrent tasks

Setting ``limit`` to ``-1`` will make all tasks run concurrently.

The default ``limit`` is ``number of cores + 4`` to a maximum of ``32``. This
(somewhat arbitrarily) reflects the default for asyncio's
``ThreadPoolExecutor``.

For network tasks it might make sense to set the concurrency ``limit`` lower
than the default, if, for example, opening many concurrent connections will
trigger rate-limiting or soak bandwidth.

If an error is raised while trying to iterate the provided coroutines, the
error is wrapped in an ``ConcurrentIteratorError`` and is raised immediately.

In this case, no further handling occurs, and ``yield_exceptions`` has no
effect.

Any errors raised while trying to create or run tasks are wrapped in
``ConcurrentError``.

Any errors raised during task execution are wrapped in
``ConcurrentExecutionError``.

If you specify ``yield_exceptions`` as ``True`` then the wrapped errors will be
yielded in the results.

If ``yield_exceptions`` is False (the default), then the wrapped error will
be raised immediately.

If you use any kind of ``Generator`` or ``AsyncGenerator`` to produce the
awaitables, and ``yield_exceptions`` is ``False``, in the event that an error
occurs, it is your responsibility to ``close`` remaining awaitables that you
might have created, but which have not already been fired.

This utility is useful for concurrency of io-bound (as opposed to cpu-bound)
tasks.

Usage
-----

Lets first create a coroutine that waits for a random amount of time,
and then returns its id and how long it waited.

.. code-block:: pycon

>>> import random

>>> async def task_to_run(task_id):
...     print(f"{task_id} starting")
...     wait = random.random() * 5
...     await asyncio.sleep(wait)
...     return task_id, wait

Next lets create an async generator that yields 10 of the coroutines.

Note that the coroutines are not awaited, they will be created as tasks.

.. code-block:: pycon

>>> def provider():
...     for task_id in range(0, 10):
...         yield task_to_run(task_id)

Finally, lets create an function to asynchronously iterate the results, and
fire it with the generator.

As we limit the concurrency to 3, the first 3 jobs start, and as the first
returns, the next one fires.

This continues until all have completed.

.. code-block:: pycon

>>> import asyncio
>>> from aio.tasks import concurrent

>>> async def run(coros):
...     async for (task_id, wait) in concurrent(coros, limit=3):
...         print(f"{task_id} waited {wait}")

>>> asyncio.run(run(provider()))
0 starting
1 starting
2 starting
... waited ...
3 starting
... waited ...
...
... waited ...
