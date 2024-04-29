
import asyncio
import gc
import inspect
import types
from typing import AsyncIterator, AsyncIterable
from unittest.mock import AsyncMock, MagicMock, PropertyMock

import pytest

import aio.core.tasks


@pytest.mark.parametrize("limit", ["XX", None, "", 0, -1, 73])
@pytest.mark.parametrize("yield_exceptions", [None, True, False])
def test_aio_concurrent_constructor(limit, yield_exceptions):
    kwargs = {}
    if limit == "XX":
        limit = None
    else:
        kwargs["limit"] = limit
    if yield_exceptions is not None:
        kwargs["yield_exceptions"] = yield_exceptions

    concurrent = aio.core.tasks.Concurrent(["CORO"], **kwargs)
    assert concurrent._coros == ["CORO"]
    assert concurrent._limit == limit
    assert (
        concurrent.yield_exceptions
        == (False
            if yield_exceptions is None
            else yield_exceptions))
    assert concurrent._running == []

    assert concurrent.running_tasks is concurrent._running
    assert "running_tasks" in concurrent.__dict__


def test_aio_concurrent_dunder_aiter(patches):
    concurrent = aio.core.tasks.Concurrent(["CORO"])
    patched = patches(
        "asyncio",
        "Concurrent.output",
        ("Concurrent.submit", dict(new_callable=MagicMock)),
        prefix="aio.core.tasks.tasks")

    with patched as (m_asyncio, m_output, m_submit):
        assert concurrent.__aiter__() == m_output.return_value

    assert concurrent.submit_task == m_asyncio.create_task.return_value
    assert (
        m_submit.call_args
        == [(), {}])
    assert (
        m_asyncio.create_task.call_args
        == [(m_submit.return_value, ), {}])


@pytest.mark.parametrize("running", [True, False])
@pytest.mark.parametrize("submitting", [True, False])
def test_aio_concurrent_active(patches, running, submitting):
    concurrent = aio.core.tasks.Concurrent(["CORO"])
    patched = patches(
        "asyncio",
        ("Concurrent.submitting", dict(new_callable=PropertyMock)),
        ("Concurrent.running", dict(new_callable=PropertyMock)),
        prefix="aio.core.tasks.tasks")

    with patched as (m_asyncio, m_submit, m_run):
        m_submit.return_value = submitting
        m_run.return_value = running
        assert concurrent.active == (submitting or running)

    assert "active" not in concurrent.__dict__


def test_aio_concurrent_closing_lock(patches):
    concurrent = aio.core.tasks.Concurrent(["CORO"])
    patched = patches(
        "asyncio",
        prefix="aio.core.tasks.tasks")

    with patched as (m_asyncio, ):
        assert concurrent.closing_lock == m_asyncio.Lock.return_value

    assert (
        m_asyncio.Lock.call_args
        == [(), {}])
    assert "closing_lock" in concurrent.__dict__


@pytest.mark.parametrize("locked", [True, False])
def test_aio_concurrent_closed(patches, locked):
    concurrent = aio.core.tasks.Concurrent(["CORO"])
    patched = patches(
        ("Concurrent.closing_lock", dict(new_callable=PropertyMock)),
        prefix="aio.core.tasks.tasks")

    with patched as (m_closing_lock, ):
        m_closing_lock.return_value.locked.return_value = locked
        assert concurrent.closed == locked

    assert "closed" not in concurrent.__dict__


@pytest.mark.parametrize("raises", [None, BaseException, GeneratorExit])
@pytest.mark.parametrize("close_raises", [None, BaseException])
async def test_aio_concurrent_coros(patches, raises, close_raises):
    concurrent = aio.core.tasks.Concurrent(["CORO"])
    patched = patches(
        ("Concurrent.iter_coros", dict(new_callable=PropertyMock)),
        prefix="aio.core.tasks.tasks")
    results = []
    return_coros = [f"CORO{i}" for i in range(0, 3)]
    m_aclose = AsyncMock()
    if close_raises:
        m_aclose.side_effect = close_raises()

    class Coros:
        aclose = m_aclose

        def __call__(self):
            return self

        async def __aiter__(self):
            if raises:
                raise raises("AN ERROR OCCURRED")
            for coro in return_coros:
                yield coro

    with patched as (m_coros, ):
        coros = Coros()
        m_coros.return_value = coros
        if raises == BaseException:
            with pytest.raises(BaseException):
                async for coro in concurrent.coros:
                    pass
        else:
            async for coro in concurrent.coros:
                results.append(coro)

    if raises == GeneratorExit:
        assert (
            coros.aclose.call_args
            == [(), {}])
        return

    assert not coros.aclose.called
    assert "coros" not in concurrent.__dict__

    if raises:
        return
    assert results == return_coros


def test_aio_concurrent_running_queue(patches):
    concurrent = aio.core.tasks.Concurrent(["CORO"])
    patched = patches(
        "asyncio",
        prefix="aio.core.tasks.tasks")

    with patched as (m_asyncio, ):
        assert concurrent.running_queue == m_asyncio.Queue.return_value

    assert (
        m_asyncio.Queue.call_args
        == [(), {}])
    assert "running_queue" in concurrent.__dict__


@pytest.mark.parametrize("cpus", [None, "", 0, 4, 73])
def test_aio_concurrent_default_limit(patches, cpus):
    concurrent = aio.core.tasks.Concurrent(["CORO"])
    patched = patches(
        "min",
        "os",
        prefix="aio.core.tasks.tasks")

    with patched as (m_min, m_os):
        m_os.cpu_count.return_value = cpus
        assert concurrent.default_limit == m_min.return_value

    assert (
        m_min.call_args
        == [(32, (cpus or 0) + 4), {}])
    assert "default_limit" not in concurrent.__dict__


def test_aio_concurrent_consumes_async(patches):
    concurrent = aio.core.tasks.Concurrent(["CORO"])
    patched = patches(
        "isinstance",
        prefix="aio.core.tasks.tasks")

    with patched as (m_inst, ):
        assert concurrent.consumes_async == m_inst.return_value

    assert (
        m_inst.call_args
        == [(["CORO"],
             (types.AsyncGeneratorType,
              AsyncIterator,
              AsyncIterable)), {}])
    assert "consumes_async" in concurrent.__dict__


def test_aio_concurrent_consumes_generator(patches):
    concurrent = aio.core.tasks.Concurrent(["CORO"])
    patched = patches(
        "isinstance",
        prefix="aio.core.tasks.tasks")

    with patched as (m_inst, ):
        assert concurrent.consumes_generator == m_inst.return_value

    assert (
        m_inst.call_args
        == [(["CORO"], (types.AsyncGeneratorType, types.GeneratorType)), {}])
    assert "consumes_generator" in concurrent.__dict__


@pytest.mark.parametrize("limit", [None, "", 0, -1, 73])
def test_aio_concurrent_limit(patches, limit):
    concurrent = aio.core.tasks.Concurrent(["CORO"])
    patched = patches(
        ("Concurrent.default_limit", dict(new_callable=PropertyMock)),
        prefix="aio.core.tasks.tasks")
    concurrent._limit = limit

    with patched as (m_limit, ):
        assert concurrent.limit == (limit or m_limit.return_value)

    if limit:
        assert not m_limit.called

    assert "limit" in concurrent.__dict__


@pytest.mark.parametrize("limit", [None, "", 0, -1, 73])
def test_aio_concurrent_nolimit(patches, limit):
    concurrent = aio.core.tasks.Concurrent(["CORO"])
    patched = patches(
        ("Concurrent.limit", dict(new_callable=PropertyMock)),
        prefix="aio.core.tasks.tasks")

    with patched as (m_limit, ):
        m_limit.return_value = limit
        assert concurrent.nolimit == (limit == -1)

    assert "nolimit" in concurrent.__dict__


def test_aio_concurrent_out(patches):
    concurrent = aio.core.tasks.Concurrent(["CORO"])
    patched = patches(
        "asyncio",
        prefix="aio.core.tasks.tasks")

    with patched as (m_asyncio, ):
        assert concurrent.out == m_asyncio.Queue.return_value

    assert (
        m_asyncio.Queue.call_args
        == [(), {}])
    assert "out" in concurrent.__dict__


@pytest.mark.parametrize("empty", [True, False])
def test_aio_concurrent_running(patches, empty):
    concurrent = aio.core.tasks.Concurrent(["CORO"])
    patched = patches(
        ("Concurrent.running_queue", dict(new_callable=PropertyMock)),
        prefix="aio.core.tasks.tasks")

    with patched as (m_running_queue, ):
        m_running_queue.return_value.empty.return_value = empty
        assert concurrent.running == (not empty)

    assert "running" not in concurrent.__dict__


def test_aio_concurrent_sem(patches):
    concurrent = aio.core.tasks.Concurrent(["CORO"])
    patched = patches(
        "asyncio",
        ("Concurrent.limit", dict(new_callable=PropertyMock)),
        prefix="aio.core.tasks.tasks")

    with patched as (m_asyncio, m_limit):
        assert concurrent.sem == m_asyncio.Semaphore.return_value

    assert (
        m_asyncio.Semaphore.call_args
        == [(m_limit.return_value, ), {}])
    assert "sem" in concurrent.__dict__


def test_aio_concurrent_submission_lock(patches):
    concurrent = aio.core.tasks.Concurrent(["CORO"])
    patched = patches(
        "asyncio",
        prefix="aio.core.tasks.tasks")

    with patched as (m_asyncio, ):
        assert concurrent.submission_lock == m_asyncio.Lock.return_value

    assert (
        m_asyncio.Lock.call_args
        == [(), {}])
    assert "submission_lock" in concurrent.__dict__


@pytest.mark.parametrize("locked", [True, False])
def test_aio_concurrent_submitting(patches, locked):
    concurrent = aio.core.tasks.Concurrent(["CORO"])
    patched = patches(
        ("Concurrent.submission_lock", dict(new_callable=PropertyMock)),
        prefix="aio.core.tasks.tasks")

    with patched as (m_submission_lock, ):
        m_submission_lock.return_value.locked.return_value = locked
        assert concurrent.submitting == locked

    assert "submitting" not in concurrent.__dict__


async def test_aio_concurrent_cancel(patches):
    concurrent = aio.core.tasks.Concurrent(["CORO"])
    patched = patches(
        ("Concurrent.cancel_tasks", dict(new_callable=AsyncMock)),
        ("Concurrent.close", dict(new_callable=AsyncMock)),
        ("Concurrent.close_coros", dict(new_callable=AsyncMock)),
        ("Concurrent.sem", dict(new_callable=PropertyMock)),
        prefix="aio.core.tasks.tasks")

    waiter = MagicMock()

    class SubmitTask:
        def __init__(self):
            self.cancel = MagicMock()

        def __await__(self):
            waiter()
            yield

    concurrent.submit_task = SubmitTask()

    with patched as (m_cancel, m_close, m_coros, m_sem):
        assert not await concurrent.cancel()

    assert (
        m_close.call_args
        == [(), {}])
    assert (
        m_sem.return_value.release.call_args
        == [(), {}])
    assert (
        m_cancel.call_args
        == [(), {}])
    assert (
        m_coros.call_args
        == [(), {}])
    assert (
        waiter.call_args
        == [(), {}])


@pytest.mark.parametrize("bad", range(0, 8))
async def test_aio_concurrent_cancel_tasks(patches, bad):
    concurrent = aio.core.tasks.Concurrent(["CORO"])
    patched = patches(
        ("Concurrent.running_tasks", dict(new_callable=PropertyMock)),
        prefix="aio.core.tasks.tasks")

    tasks = []
    waiter = MagicMock()

    class Task:
        def __init__(self, i):
            self.i = i
            self.cancel = MagicMock()

        def __await__(self):
            waiter()
            if self.i == bad:
                raise BaseException("AN ERROR OCCURRED")

    for i in range(0, 7):
        tasks.append(Task(i))

    with patched as (m_running, ):
        m_running.return_value = tasks
        assert not await concurrent.cancel_tasks()

    assert (
        waiter.call_args_list
        == [[(), {}]] * 7)
    for task in tasks:
        assert (
            task.cancel.call_args
            == [(), {}])


@pytest.mark.parametrize("closed", [True, False])
async def test_aio_concurrent_close(patches, closed):
    concurrent = aio.core.tasks.Concurrent(["CORO"])
    patched = patches(
        ("Concurrent.closed", dict(new_callable=PropertyMock)),
        ("Concurrent.closing_lock", dict(new_callable=PropertyMock)),
        prefix="aio.core.tasks.tasks")

    with patched as (m_closed, m_lock):
        m_closed.return_value = closed
        m_lock.return_value.acquire = AsyncMock()
        assert not await concurrent.close()

    if closed:
        assert not m_lock.called
    else:
        assert (
            m_lock.return_value.acquire.call_args
            == [(), {}])


@pytest.mark.parametrize("consumes_generator", [True, False])
@pytest.mark.parametrize("bad", range(0, 8))
async def test_aio_concurrent_close_coros(patches, consumes_generator, bad):
    concurrent = aio.core.tasks.Concurrent(["CORO"])
    patched = patches(
        "Concurrent.close",
        ("Concurrent.iter_coros", dict(new_callable=PropertyMock)),
        ("Concurrent.consumes_generator", dict(new_callable=PropertyMock)),
        prefix="aio.core.tasks.tasks")

    coros = []
    for i in range(0, 7):
        coro = MagicMock()
        if i == bad:
            coro.close.side_effect = BaseException("AN ERROR OCCURRED")
        coros.append(coro)

    async def iter_coros():
        for coro in coros:
            yield coro

    with patched as (m_close, m_iter, m_isgen):
        m_isgen.return_value = consumes_generator
        m_iter.return_value = iter_coros
        assert not await concurrent.close_coros()

    if consumes_generator:
        assert not m_iter.called
        return
    assert (
        m_iter.call_args
        == [(), {}])
    for coro in coros:
        assert (
            coro.close.call_args
            == [(), {}])


async def test_aio_concurrent_create_task(patches):
    concurrent = aio.core.tasks.Concurrent(["CORO"])
    patched = patches(
        "asyncio",
        "Concurrent.remember_task",
        ("Concurrent.task", dict(new_callable=MagicMock)),
        ("Concurrent.running_queue", dict(new_callable=PropertyMock)),
        prefix="aio.core.tasks.tasks")

    with patched as (m_asyncio, m_rem, m_task, m_running_queue):
        assert not await concurrent.create_task("CORO")

    assert (
        m_running_queue.return_value.put_nowait.call_args
        == [(None, ), {}])
    assert (
        m_task.call_args
        == [("CORO", ), {}])
    assert (
        m_asyncio.create_task.call_args
        == [(m_task.return_value, ), {}])
    assert (
        m_rem.call_args
        == [(m_asyncio.create_task.return_value, ), {}])


@pytest.mark.parametrize("closed", [True, False])
@pytest.mark.parametrize("active", [True, False])
async def test_aio_concurrent_exit_on_completion(patches, active, closed):
    concurrent = aio.core.tasks.Concurrent(["CORO"])
    patched = patches(
        ("Concurrent.active", dict(new_callable=PropertyMock)),
        ("Concurrent.closed", dict(new_callable=PropertyMock)),
        ("Concurrent.out", dict(new_callable=PropertyMock)),
        prefix="aio.core.tasks.tasks")

    with patched as (m_active, m_closed, m_out):
        m_out.return_value.put = AsyncMock()
        m_active.return_value = active
        m_closed.return_value = closed
        assert not await concurrent.exit_on_completion()

    if closed or active:
        assert not m_out.called
        return
    assert (
        m_out.return_value.put.call_args
        == [(aio.core.tasks.tasks._sentinel, ), {}])


@pytest.mark.parametrize("closed", [True, False])
def test_aio_concurrent_forget_task(patches, closed):
    concurrent = aio.core.tasks.Concurrent(["CORO"])
    patched = patches(
        ("Concurrent.closed", dict(new_callable=PropertyMock)),
        prefix="aio.core.tasks.tasks")
    concurrent._running = MagicMock()

    with patched as (m_closed, ):
        m_closed.return_value = closed
        assert not concurrent.forget_task("TASK")

    if closed:
        assert not concurrent._running.remove.called
        return
    assert (
        concurrent._running.remove.call_args
        == [("TASK", ), {}])


@pytest.mark.parametrize("raises", [True, False])
@pytest.mark.parametrize("consumes_async", [True, False])
async def test_aio_concurrent_iter_coros(patches, raises, consumes_async):
    concurrent = aio.core.tasks.Concurrent(["CORO"])
    patched = patches(
        ("Concurrent.consumes_async", dict(new_callable=PropertyMock)),
        prefix="aio.core.tasks.tasks")

    coros = [f"CORO{i}" for i in range(0, 7)]
    exception = BaseException("AN RAISES OCCURRED")

    def iter_coros():
        if raises:
            raise exception
        for coro in coros:
            yield coro

    async def async_iter_coros():
        if raises:
            raise exception
        for coro in coros:
            yield coro

    concurrent._coros = (
        async_iter_coros()
        if consumes_async
        else iter_coros())
    results = []

    with patched as (m_async, ):
        m_async.return_value = consumes_async

        async for result in concurrent.iter_coros():
            results.append(result)

    if raises:
        error = results[0]
        assert isinstance(error, aio.core.tasks.ConcurrentIteratorError)
        assert error.args[0] is exception
        assert results == [error]
        return
    assert results == coros


@pytest.mark.parametrize("closed", [True, False])
@pytest.mark.parametrize("nolimit", [True, False])
@pytest.mark.parametrize("decrement", [None, True, False])
async def test_aio_concurrent_on_task_complete(
        patches, closed, nolimit, decrement):
    concurrent = aio.core.tasks.Concurrent(["CORO"])
    patched = patches(
        ("Concurrent.exit_on_completion", dict(new_callable=AsyncMock)),
        ("Concurrent.closed", dict(new_callable=PropertyMock)),
        ("Concurrent.out", dict(new_callable=PropertyMock)),
        ("Concurrent.running_queue", dict(new_callable=PropertyMock)),
        ("Concurrent.nolimit", dict(new_callable=PropertyMock)),
        ("Concurrent.sem", dict(new_callable=PropertyMock)),
        prefix="aio.core.tasks.tasks")
    kwargs = {}
    if decrement is not None:
        kwargs["decrement"] = decrement

    with patched as patchy:
        (m_complete, m_closed, m_out,
         m_running_queue, m_nolimit, m_sem) = patchy
        m_nolimit.return_value = nolimit
        m_closed.return_value = closed
        m_out.return_value.put = AsyncMock()
        assert not await concurrent.on_task_complete("RESULT", **kwargs)

    if closed:
        assert not m_complete.called
        assert not m_nolimit.called
        assert not m_sem.called
        assert not m_running_queue.called
        assert not m_out.return_value.put.called
        return

    assert (
        m_out.return_value.put.call_args
        == [("RESULT", ), {}])
    if nolimit:
        assert not m_sem.return_value.release.called
    else:
        assert (
            m_sem.return_value.release.call_args
            == [(), {}])
    if decrement or decrement is None:
        assert (
            m_running_queue.return_value.get_nowait.call_args
            == [(), {}])
    else:
        assert not m_running_queue.return_value.get_nowait.called
    assert (
        m_complete.call_args
        == [(), {}])


@pytest.mark.parametrize("result_count", range(0, 7))
@pytest.mark.parametrize("error", [True, False])
@pytest.mark.parametrize("should_error", [True, False])
async def test_aio_concurrent_output(
        patches, result_count, error, should_error):
    concurrent = aio.core.tasks.Concurrent(["CORO"])
    patched = patches(
        "Concurrent.raisable",
        ("Concurrent.cancel", dict(new_callable=AsyncMock)),
        ("Concurrent.close", dict(new_callable=AsyncMock)),
        ("Concurrent.out", dict(new_callable=PropertyMock)),
        prefix="aio.core.tasks.tasks")

    class DummyException(Exception):
        pass

    exception = DummyException()

    class DummyQueue:
        _running_queue = 0

        async def get(self):
            if result_count == 0:
                return aio.core.tasks.tasks._sentinel
            if result_count > self._running_queue:
                self._running_queue += 1
                if error and result_count == self._running_queue:
                    return exception
                return f"RESULT {self._running_queue}"
            return aio.core.tasks.tasks._sentinel

        def raisable(self, result):
            _should_error = (
                error
                and should_error
                and (result_count == self._running_queue))
            if not _should_error:
                return None
            return exception

    q = DummyQueue()
    results = []

    with patched as (m_error, m_cancel, m_close, m_out):
        m_out.return_value.get.side_effect = q.get
        m_error.side_effect = q.raisable
        if result_count and error and should_error:
            with pytest.raises(DummyException):
                async for result in concurrent.output():
                    results.append(result)
        else:
            async for result in concurrent.output():
                results.append(result)

    if result_count and error and should_error:
        # last one errored
        assert results == [f"RESULT {i}" for i in range(1, result_count)]
        assert (
            m_error.call_args_list
            == [[(result,), {}] for result in results] + [[(exception,), {}]])
        assert (
            m_cancel.call_args
            == [(), {}])
        assert not m_close.called
        return

    assert (
        m_close.call_args_list
        == [[(), {}]])
    assert not m_cancel.called

    if not result_count:
        assert results == []
        return

    if error:
        assert (
            results
            == [f"RESULT {i}" for i in range(1, result_count)] + [exception])
        return
    # all results returned correctly
    assert (
        results
        == [f"RESULT {i}" for i in range(1, result_count + 1)])


@pytest.mark.parametrize("closed_before", [True, False])
@pytest.mark.parametrize("closed_after", [True, False])
@pytest.mark.parametrize("nolimit", [True, False])
async def test_aio_concurrent_ready(
        patches, closed_before, closed_after, nolimit):
    concurrent = aio.core.tasks.Concurrent(["CORO"])
    patched = patches(
        ("Concurrent.closed", dict(new_callable=PropertyMock)),
        ("Concurrent.nolimit", dict(new_callable=PropertyMock)),
        ("Concurrent.sem", dict(new_callable=PropertyMock)),
        prefix="aio.core.tasks.tasks")

    class DummyCloser:
        order_mock = MagicMock()
        close_calls = 0

        async def _acquire(self):
            self.order_mock("ACQUIRE")

        def _nolimit(self):
            self.order_mock("NOLIMIT")
            return nolimit

        def _closed(self):
            self.order_mock("CLOSED")
            self.close_calls += 1
            if self.close_calls == 1:
                return closed_before
            if self.close_calls == 2:
                return closed_after

    closer = DummyCloser()

    with patched as (m_closed, m_nolimit, m_sem):
        m_nolimit.side_effect = closer._nolimit
        m_closed.side_effect = closer._closed
        m_sem.return_value.acquire = closer._acquire
        assert (
            await concurrent.ready()
            == ((not closed_before and not closed_after)
                if not nolimit else not closed_before))

    if closed_before:
        assert not m_nolimit.called
        assert not m_sem.called
        assert (
            closer.order_mock.call_args_list
            == [[('CLOSED',), {}]])
        return
    if nolimit:
        assert not m_sem.called
        assert (
            closer.order_mock.call_args_list
            == [[('CLOSED',), {}],
                [('NOLIMIT',), {}]])
        return
    assert (
        closer.order_mock.call_args_list
        == [[('CLOSED',), {}],
            [('NOLIMIT',), {}],
            [('ACQUIRE',), {}],
            [('CLOSED',), {}]])


def test_aio_concurrent_remember_task():
    concurrent = aio.core.tasks.Concurrent(["CORO"])
    concurrent._running = MagicMock()
    task = MagicMock()
    assert not concurrent.remember_task(task)
    assert (
        concurrent._running.append.call_args
        == [(task, ), {}])
    assert (
        task.add_done_callback.call_args
        == [(concurrent.forget_task, ), {}])


@pytest.mark.parametrize(
    "result",
    [None,
     "RESULT",
     aio.core.tasks.ConcurrentError,
     aio.core.tasks.ConcurrentExecutionError,
     aio.core.tasks.ConcurrentIteratorError])
@pytest.mark.parametrize("yield_exceptions", [True, False])
@pytest.mark.parametrize("cause", [None, "FAILURE"])
def test_aio_concurrent_raisable(result, yield_exceptions, cause):
    concurrent = aio.core.tasks.Concurrent(["CORO"])
    concurrent.yield_exceptions = yield_exceptions
    arg1 = MagicMock()
    arg2 = MagicMock()

    if isinstance(result, type) and issubclass(result, BaseException):
        wrapped = BaseException(cause, arg1, arg2)
        result = result(wrapped)

    should_error = (
        (isinstance(result, aio.core.tasks.ConcurrentIteratorError)
         or (isinstance(result, aio.core.tasks.ConcurrentError)
             and not yield_exceptions)))
    returned = concurrent.raisable(result)
    if not should_error:
        assert returned is None
        return
    assert type(returned) is type(result)
    assert type(returned.args[0]) is BaseException
    assert returned.args[0].args[0] == (str(cause) if cause else None)
    assert returned.args[0].args[1] == arg1
    assert returned.args[0].args[2] == arg2


@pytest.mark.parametrize("coros", range(0, 7))
@pytest.mark.parametrize("unready", range(0, 8))
@pytest.mark.parametrize(
    "valid_raises", [None, Exception, aio.core.tasks.ConcurrentError])
@pytest.mark.parametrize("iter_errors", [True, False])
async def test_aio_concurrent_submit(
        patches, coros, unready, valid_raises, iter_errors):
    concurrent = aio.core.tasks.Concurrent(["CORO"])
    patched = patches(
        "isinstance",
        "Concurrent.validate_coro",
        ("Concurrent.exit_on_completion", dict(new_callable=AsyncMock)),
        ("Concurrent.create_task", dict(new_callable=AsyncMock)),
        ("Concurrent.on_task_complete", dict(new_callable=AsyncMock)),
        ("Concurrent.ready", dict(new_callable=AsyncMock)),
        ("Concurrent.coros", dict(new_callable=PropertyMock)),
        ("Concurrent.out", dict(new_callable=PropertyMock)),
        ("Concurrent.submission_lock", dict(new_callable=PropertyMock)),
        prefix="aio.core.tasks.tasks")
    m_order = MagicMock()

    class DummyReady:
        counter = 0

        def ready(self):
            if self.counter >= unready:
                self.counter += 1
                return False
            self.counter += 1
            return True

    ready = DummyReady()

    async def acquire():
        m_order("ACQUIRE")

    def release():
        m_order("RELEASE")

    corolist = [MagicMock() for coro in range(1, coros)]

    async def iter_coros():
        for coro in corolist:
            m_order(coro)
            yield coro

    valid_errors = (
        (valid_raises == Exception)
        and coros > 1
        and not unready == 0
        and not iter_errors)

    with patched as patchy:
        (m_inst, m_valid, m_exit, m_create,
         m_complete, m_ready, m_coros, m_out, m_lock) = patchy
        m_out.return_value.put = AsyncMock()
        m_inst.return_value = iter_errors
        m_valid.side_effect = valid_raises
        m_ready.side_effect = ready.ready
        m_coros.return_value = iter_coros()
        m_lock.return_value.acquire.side_effect = acquire
        m_lock.return_value.release.side_effect = release

        if valid_errors:
            with pytest.raises(Exception):
                await concurrent.submit()
        else:
            assert not await concurrent.submit()

    if valid_errors:
        assert not m_lock.return_value.called
        assert not m_exit.called
    else:
        assert (
            m_lock.return_value.release.call_args
            == [(), {}])
        assert (
            m_exit.call_args
            == [(), {}])

    if coros < 2:
        assert not m_valid.called
        assert not m_inst.called
        assert not m_complete.called
        assert not m_create.called
        assert not m_ready.called
        assert not m_out.return_value.put.called
        return

    should_close_coro = (
        not iter_errors
        and not valid_errors
        and (len(corolist) > unready))

    if should_close_coro:
        assert corolist[unready].close.called
    else:
        assert not any(coro.close.called for coro in corolist)

    if iter_errors:
        assert (
            m_out.return_value.put.call_args_list
            == [[(corolist[0], ), {}]])
        assert (
            m_inst.call_args_list
            == [[(corolist[0], aio.core.tasks.ConcurrentIteratorError), {}]])
        assert not m_ready.called
        assert not m_valid.called
        assert not m_complete.called
        assert not m_create.called
        return

    if valid_errors:
        assert (
            m_inst.call_args_list
            == [[(corolist[0], aio.core.tasks.ConcurrentIteratorError), {}]])
        assert (
            m_ready.call_args_list
            == [[(), {}]])
        assert (
            m_valid.call_args_list
            == [[(corolist[0], ), {}]])
        assert not m_complete.called
        assert not m_create.called
        assert (
            m_order.call_args_list
            == ([[('ACQUIRE',), {}],
                 [(corolist[0],), {}]]))
        return

    assert not m_out.return_value.put.called
    assert (
        m_ready.call_args_list
        == [[(), {}]] * min(coros - 1, unready + 1 or 1))
    assert (
        m_valid.call_args_list
        == [[(corolist[i - 1], ), {}]
            for i in range(1, min(coros, unready + 1))])
    assert (
        m_order.call_args_list
        == ([[('ACQUIRE',), {}]]
            + [[(corolist[i - 1],), {}]
               for i in range(1, min(coros, unready + 2))]
            + [[('RELEASE',), {}]]))
    if valid_raises:
        assert (
            len(m_complete.call_args_list)
            == max(min(coros - 1, unready), 0))
        for c in m_complete.call_args_list:
            error = list(c)[0][0]
            assert isinstance(error, aio.core.tasks.ConcurrentError)
            assert (
                c
                == [(error,), {'decrement': False}])
        assert not m_create.called
        return
    assert not m_complete.called
    assert (
        m_create.call_args_list
        == [[(corolist[i - 1],), {}]
            for i in range(1, min(coros, unready + 1))])


class OtherException(BaseException):
    pass


@pytest.mark.parametrize("raises", [None, Exception, OtherException])
async def test_aio_concurrent_task(patches, raises):
    concurrent = aio.core.tasks.Concurrent(["CORO"])
    patched = patches(
        "Concurrent.on_task_complete",
        prefix="aio.core.tasks.tasks")

    if raises:
        exception = raises("AN ERROR OCCURRED")

    async def coro():
        if raises:
            raise exception
        return 23

    with patched as (m_complete, ):
        assert not await concurrent.task(coro())

    result = m_complete.call_args[0][0]

    if not raises:
        assert result == 23
    else:
        assert isinstance(result, aio.core.tasks.ConcurrentExecutionError)
        assert result.args[0] is exception
    assert (
        m_complete.call_args
        == [(result, ), {}])


@pytest.mark.parametrize("awaitable", [True, False])
@pytest.mark.parametrize(
    "state",
    [inspect.CORO_CLOSED,
     inspect.CORO_CREATED,
     inspect.CORO_RUNNING,
     inspect.CORO_SUSPENDED])
def test_aio_concurrent_validate_coro(patches, awaitable, state):
    concurrent = aio.core.tasks.Concurrent(["CORO"])
    patched = patches(
        "inspect.getcoroutinestate",
        prefix="aio.core.tasks.tasks")

    # we cant patch inspect.isawaitable without fooing unittest
    def unawaitable():
        pass

    async def coro():
        pass

    awaits = (
        coro()
        if awaitable
        else unawaitable)

    with patched as (m_state, ):
        m_state.return_value = state

        if awaitable and state == inspect.CORO_CREATED:
            assert not concurrent.validate_coro(awaits)
        else:
            with pytest.raises(aio.core.tasks.ConcurrentError) as e:
                concurrent.validate_coro(awaits)

    if not awaitable:
        assert (
            e.value.args[0]
            == f'Provided input was not a coroutine: {awaits}')
        assert not m_state.called
        return

    awaits.close()
    assert (
        m_state.call_args
        == [(awaits, ), {}])

    if state != inspect.CORO_CREATED:
        assert (
            e.value.args[0]
            == f'Provided coroutine has already been fired: {awaits}')


async def aiter(items):
    for item in items:
        yield item


@pytest.mark.parametrize("limit", list(range(0, 4)) + [-1])
@pytest.mark.parametrize("yield_exceptions", [None, True, False])
@pytest.mark.parametrize("iter_type", [list, tuple, set, iter, aiter])
@pytest.mark.parametrize(
    "coros",
    [["HAPPY"],
     ["HAPPY"] * 2 + ["SAD"] + ["HAPPY"] * 3,
     ["HAPPY"] * 7,
     ["HAPPY"] * 2 + ["RAISE"] + ["HAPPY"] * 3,
     ["SAD"] * 2 + ["HAPPY"] * 3,
     ["HAPPY"] * 2 + ["CABBAGE"] + ["HAPPY"] * 3,
     ["HAPPY"] * 2 + ["FIRED"] + ["HAPPY"] * 3])
async def test_aio_concurrent_integration(
        limit, yield_exceptions, iter_type, coros):
    # This is an integration/black-box test that only measures inputs/outputs
    # and the effect of using the utility with them on them

    # `HAPPY` - a happy coroutine ready to be fired
    # `SAD` - a sad coroutine that will raise a `SadError` when fired
    # `FIRED` - a coroutine that has already been fired
    # `RAISE` - raise an error in the iterator
    # `CABBAGE` - leafy vegetable of the brassica family

    tasks_at_the_beginning = len(asyncio.all_tasks())

    kwargs = {}

    if yield_exceptions is not None:
        kwargs["yield_exceptions"] = yield_exceptions

    if limit:
        kwargs["limit"] = limit

    class SadError(Exception):
        pass

    class LoopError(Exception):
        pass

    async def happy():
        # this makes happy return after sad (ie errors) and tests the ordering
        # of responses and the handling of pending tasks when errors occur
        await asyncio.sleep(.01)
        return "HAPPY"

    fired = happy()
    await fired

    async def sad():
        raise SadError

    def coro_gen():
        for coro in coros:
            if coro == "RAISE":
                raise LoopError()
            if coro == "HAPPY":
                yield happy()
            elif coro == "SAD":
                yield sad()
            elif coro == "FIRED":
                yield fired
            else:
                yield coro

    all_good = all(coro == "HAPPY" for coro in coros)
    iter_raises = any(coro == "RAISE" for coro in coros)

    if iter_raises:
        # we can only test the generator types for errors
        # during iteration - ie if `list`, `tuple` etc contain
        # errors, they would raise now.
        if iter_type not in [iter, aiter]:
            return
        generated_coros = coro_gen()
    else:
        generated_coros = list(coro_gen())
        expected_err_index = next(
            (i for i, x in enumerate(coros)
             if x != 'HAPPY'),
            None)

    results = []
    concurrent = aio.core.tasks.Concurrent(
        iter_type(generated_coros), **kwargs)

    if (not all_good and not yield_exceptions) or iter_raises:
        if iter_raises:
            with pytest.raises(aio.core.tasks.ConcurrentIteratorError) as e:
                async for result in concurrent:
                    results.append(result)
            assert isinstance(e.value.args[0], LoopError)
            return
        else:
            coro_fail = (
                any(not inspect.isawaitable(coro) for coro in generated_coros)
                or any(coro == "FIRED" for coro in coros))
            if coro_fail:
                with pytest.raises(aio.core.tasks.ConcurrentError):
                    async for result in concurrent:
                        results.append(result)
            else:
                with pytest.raises(aio.core.tasks.ConcurrentExecutionError):
                    async for result in concurrent:
                        results.append(result)

        # for iterators there is no way of knowing that more awaitables were
        # on the way when failure happened, so these need to be closed here
        if iter_type in (iter, aiter):
            for coro in generated_coros[expected_err_index:]:
                if not isinstance(coro, str):
                    coro.close()

        if limit < 1 and iter_type != set:
            # as all jobs are submitted concurrently (the default is higher
            # than the number of test jobs, and -1 forces no limit) and as sad
            # is faster than happy, we get no results
            assert results == []
        elif iter_type != set:
            # because the ordering on sets is indeterminate the results are
            # unpredictable therefore the easiest thing is to just exclude them
            # from this test
            assert (
                results
                == coros[:expected_err_index - (expected_err_index % limit)])

        # this can probs be removed, i think it was caused by unhandled
        # GeneratorExit
        await asyncio.sleep(.001)
        gc.collect()
        assert len(asyncio.all_tasks()) == tasks_at_the_beginning
        return

    async for result in concurrent:
        results.append(result)

    assert len(asyncio.all_tasks()) == tasks_at_the_beginning

    def mangled_results():
        # replace the errors with the test strings
        for result in results:
            if isinstance(result, aio.core.tasks.ConcurrentExecutionError):
                yield "SAD"
            elif isinstance(result, aio.core.tasks.ConcurrentError):
                if "CABBAGE" in result.args[0]:
                    yield "CABBAGE"
                else:
                    yield "FIRED"
            else:
                yield result

    if expected_err_index:
        err_index = (
            expected_err_index
            if limit == 0
            else expected_err_index - (expected_err_index % limit))

    if expected_err_index and err_index >= limit and limit not in [0, -1]:
        # the error is at the beginning of whichever batch its in
        expected = ["HAPPY"] * 6
        expected[err_index] = coros[err_index]
    else:
        # the error is in the first batch so its at the beginning
        expected = (
            [x for x in list(coros) if x != "HAPPY"]
            + [x for x in list(coros) if x == "HAPPY"])

    if iter_type == set:
        assert set(expected) == set(mangled_results())
    else:
        assert expected == list(mangled_results())


@pytest.mark.parametrize(
    "iterable",
    [[], [f"OBJ{i}" for i in range(0, 5)]])
@pytest.mark.parametrize("limit", [None, *range(0, 5)])
@pytest.mark.parametrize("yield_exceptions", [None, True, False])
async def test_inflate(patches, iterable, limit, yield_exceptions):
    patched = patches(
        "asyncio",
        "concurrent",
        prefix="aio.core.tasks.tasks")
    kwargs = {}
    if limit is not None:
        kwargs["limit"] = limit
    if yield_exceptions is not None:
        kwargs["yield_exceptions"] = yield_exceptions
    cb = MagicMock()
    awaitables = [f"AWAIT{i}" for i in range(0, 3)]
    things = [[f"RESULT{i}", "X"] for i in range(0, 7)]
    cb.return_value = awaitables
    results = []
    gathered = []

    async def iter_things(x, **kwargs):
        for thing in things:
            yield thing

    with patched as (m_aio, m_concurrent):
        m_concurrent.side_effect = iter_things
        async for thing in aio.core.tasks.inflate(iterable, cb, **kwargs):
            results.append(thing)
        gen = m_concurrent.call_args[0][0]
        for item in gen:
            gathered.append(item)

    passed_kwargs = dict(limit=limit, yield_exceptions=yield_exceptions)
    assert results == [t[0] for t in things]
    assert (
        m_concurrent.call_args
        == [(gen, ), passed_kwargs])
    assert (
        gathered
        == [m_aio.gather.return_value] * len(iterable))
    assert (
        m_aio.gather.call_args_list
        == [[(m_aio.sleep.return_value, *awaitables),
             dict(return_exceptions=True)]
            for i in range(0, len(iterable))])
    assert (
        m_aio.sleep.call_args_list
        == [[(0, ), dict(result=item)]
            for item in iterable])
    assert (
        cb.call_args_list
        == [[(item, ), {}]
            for item in iterable])


@pytest.mark.parametrize(
    "args", [[], [f"A{i}" for i in range(0, 3)]])
@pytest.mark.parametrize(
    "kwargs", [{}, {f"K{i}": f"V{i}" for i in range(0, 3)}])
@pytest.mark.parametrize("collector", [None, False, "COLLECTOR"])
@pytest.mark.parametrize("iterator", [None, False, "ITERATOR"])
@pytest.mark.parametrize("predicate", [None, False, "PREDICATE"])
@pytest.mark.parametrize("result", [None, False, "RESULT"])
async def test_concurrent(
        patches, args, kwargs, collector, iterator, predicate, result):
    patched = patches(
        "AwaitableGenerator",
        "Concurrent",
        prefix="aio.core.tasks.tasks")
    if collector is not None:
        kwargs["collector"] = collector
    if iterator is not None:
        kwargs["iterator"] = iterator
    if predicate is not None:
        kwargs["predicate"] = predicate
    if result is not None:
        kwargs["result"] = result

    with patched as (m_generator, m_concurrent):
        assert (
            aio.core.tasks.concurrent(*args, **kwargs)
            == m_generator.return_value)

    for k in ["collector", "iterator", "predicate", "result"]:
        kwargs.pop(k, None)

    assert (
        m_generator.call_args
        == [(m_concurrent.return_value, ),
            dict(collector=collector,
                 iterator=iterator,
                 predicate=predicate,
                 result=result)])
    assert (
        m_concurrent.call_args
        == [tuple(args), kwargs])
