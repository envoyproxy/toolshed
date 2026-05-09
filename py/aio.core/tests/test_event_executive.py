
import types
from functools import partial
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import AsyncMock, MagicMock, PropertyMock

import pytest

import abstracts

from aio.core import event


@abstracts.implementer(event.IExecutive)
class DummyExecutiveIface():

    @property
    def loop(self):
        return event.IExecutive.loop.fget(self)

    @property
    def pool(self):
        return event.IExecutive.pool.fget(self)

    async def execute(self, command, *args, **kwargs):
        return await event.IExecutive.execute(
            command, *args, **kwargs)

    async def execute_in_batches(self, command, *args, **kwargs):
        return await event.IExecutive.execute_in_batches(
            command, *args, **kwargs)


@abstracts.implementer(event.IExecutive)
class DummyExecutive(event.AExecutive):
    pass


async def test_event_executive_iface_constructor():

    with pytest.raises(TypeError):
        event.IExecutive()

    executive = DummyExecutiveIface()
    for iface_prop in ["loop", "pool"]:
        with pytest.raises(NotImplementedError):
            getattr(executive, iface_prop)
    for async_iface_method in ["execute", "execute_in_batches"]:
        with pytest.raises(NotImplementedError):
            await getattr(executive, async_iface_method)("EXECUTABLE")


def test_event_executive_constructor():
    assert DummyExecutive()


@pytest.mark.parametrize(
    "args", [[], [f"ARG{i}" for i in range(0, 5)]])
@pytest.mark.parametrize(
    "kwargs", [{}, {f"K{i}": f"V{i}" for i in range(0, 5)}])
async def test_event_executive_execute(patches, args, kwargs):
    executive = DummyExecutive()
    executable = MagicMock()
    patched = patches(
        ("AExecutive.loop",
         dict(new_callable=PropertyMock)),
        ("AExecutive.pool",
         dict(new_callable=PropertyMock)),
        prefix="aio.core.event.executive")

    with patched as (m_loop, m_pool):
        execute = AsyncMock()
        m_loop.return_value.run_in_executor = execute
        assert (
            await DummyExecutive.execute.__wrapped__(
                executive, executable, *args, **kwargs)
            == m_loop.return_value.run_in_executor.return_value)

    (called_args, called_kwargs) = (
        m_loop.return_value.run_in_executor.call_args)
    assert called_kwargs == {}
    assert called_args[0] == m_pool.return_value
    assert called_args[2:] == tuple(args)

    if kwargs:
        assert type(called_args[1]) is partial
        assert called_args[1].func == executable
        assert called_args[1].keywords == kwargs
    else:
        assert called_args[1] == executable


async def test_event_executive_execute_forwards_kwargs():
    executive = DummyExecutive()
    calls = []

    def executable(*args, **kwargs):
        calls.append((args, kwargs))
        return (args, kwargs)

    with ThreadPoolExecutor() as pool:
        executive._pool = pool
        result = await executive.execute(
            executable, 1, 2, foo="bar")

    assert result == ((1, 2), {"foo": "bar"})
    assert calls == [((1, 2), {"foo": "bar"})]


@pytest.mark.parametrize(
    "args", [[], [f"ARG{i}" for i in range(0, 5)]])
@pytest.mark.parametrize(
    "kwargs", [{}, {f"K{i}": f"V{i}" for i in range(0, 5)}])
@pytest.mark.parametrize("concurrency", [None, *range(0, 5)])
@pytest.mark.parametrize("max_batch_size", [None, *range(0, 5)])
@pytest.mark.parametrize("min_batch_size", [None, *range(0, 5)])
async def test_event_executive_execute_in_batches(
        iters, patches, args, kwargs, concurrency, max_batch_size,
        min_batch_size):
    executive = DummyExecutive()
    patched = patches(
        "functional",
        "tasks",
        ("AExecutive.execute",
         dict(new_callable=MagicMock)),
        prefix="aio.core.event.executive")
    call_kwargs = kwargs.copy()
    c_kwargs = {}
    if concurrency is not None:
        call_kwargs["concurrency"] = concurrency
    if max_batch_size is not None:
        call_kwargs["max_batch_size"] = max_batch_size
    if min_batch_size is not None:
        call_kwargs["min_batch_size"] = min_batch_size
    c_kwargs["limit"] = concurrency
    batches = iters()

    with patched as (m_func, m_tasks, m_exec):
        concurrent = AsyncMock()
        m_tasks.concurrent.side_effect = concurrent
        m_func.batch_jobs.return_value = batches
        assert (
            await executive.execute_in_batches(
                "EXECUTABLE",
                *args,
                **call_kwargs)
            == concurrent.return_value)
        task_iter = concurrent.call_args[0][0]
        assert isinstance(task_iter, types.GeneratorType)
        assert (
            list(task_iter)
            == [m_exec.return_value] * 5)

    assert (
        concurrent.call_args
        == [(task_iter, ), c_kwargs])
    assert (
        m_func.batch_jobs.call_args
        == [(tuple(args), ),
            dict(max_batch_size=max_batch_size,
                 min_batch_size=min_batch_size)])
    assert (
        m_exec.call_args_list
        == [[("EXECUTABLE", *batch), kwargs]
            for batch
            in batches])
