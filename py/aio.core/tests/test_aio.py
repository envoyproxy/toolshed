
from unittest.mock import AsyncMock, MagicMock

import pytest

import aio.core.subprocess


async def test_subprocess_parallel(patches):
    patched = patches(
        "asyncio",
        "ProcessPoolExecutor",
        ("AsyncSubprocess.run", dict(new_callable=MagicMock)),
        prefix="aio.core.subprocess.async_subprocess")
    procs = [f"PROC{i}" for i in range(0, 3)]
    kwargs = {f"KEY{i}": f"VALUE{i}" for i in range(0, 3)}

    async def async_result(result):
        return result

    with patched as (m_asyncio, m_future, m_run):
        returned = [f"RESULT{i}" for i in range(0, 5)]
        m_asyncio.as_completed.return_value = [
            async_result(result) for result in returned]

        results = []
        iterator = aio.core.subprocess.AsyncSubprocess.parallel(
            procs, **kwargs)
        async for result in iterator:
            results.append(result)

    assert results == returned
    assert (
        m_future.call_args
        == [(), {}])
    assert (
        m_asyncio.as_completed.call_args
        == [(tuple(
            m_asyncio.ensure_future.return_value
            for i in range(0, len(procs))), ), {}])
    kwargs["executor"] = m_future.return_value.__enter__.return_value
    assert (
        m_run.call_args_list
        == [[(proc,), kwargs] for proc in procs])
    assert (
        m_asyncio.ensure_future.call_args_list
        == [[(m_run.return_value,), {}] for proc in procs])


@pytest.mark.parametrize("loop", [True, False])
@pytest.mark.parametrize("executor", [None, "EXECUTOR"])
async def test_subprocess_run(patches, loop, executor):
    patched = patches(
        "asyncio",
        "partial",
        "subprocess",
        prefix="aio.core.subprocess.async_subprocess")
    args = [f"ARG{i}" for i in range(0, 3)]
    kwargs = {f"KEY{i}": f"VALUE{i}" for i in range(0, 3)}

    if loop:
        kwargs["loop"] = AsyncMock()

    if executor:
        kwargs["executor"] = executor

    with patched as (m_asyncio, m_partial, m_subproc):
        m_asyncio.get_running_loop.return_value = AsyncMock()
        if loop:
            m_loop = kwargs["loop"]
        else:
            m_loop = m_asyncio.get_running_loop.return_value

        assert (
            await aio.core.subprocess.run(*args, **kwargs)
            == m_loop.run_in_executor.return_value)

    if loop:
        assert not m_asyncio.get_running_loop.called

    kwargs.pop("executor", None)
    kwargs.pop("loop", None)

    assert (
        m_partial.call_args
        == [(m_subproc.run, ) + tuple(args), kwargs])
    assert (
        m_loop.run_in_executor.call_args
        == [(executor, m_partial.return_value), {}])


@pytest.mark.parametrize(
    "args", [[], [f"A{i}" for i in range(0, 3)]])
@pytest.mark.parametrize(
    "kwargs", [{}, {f"K{i}": f"V{i}" for i in range(0, 3)}])
@pytest.mark.parametrize("collector", [None, False, "COLLECTOR"])
@pytest.mark.parametrize("iterator", [None, False, "ITERATOR"])
@pytest.mark.parametrize("predicate", [None, False, "PREDICATE"])
@pytest.mark.parametrize("result", [None, False, "RESULT"])
async def test_parallel(
        patches, args, kwargs, collector, iterator, predicate, result):
    patched = patches(
        "functional",
        "AsyncSubprocess.parallel",
        prefix="aio.core.subprocess.async_subprocess")
    if collector is not None:
        kwargs["collector"] = collector
    if iterator is not None:
        kwargs["iterator"] = iterator
    if predicate is not None:
        kwargs["predicate"] = predicate
    if result is not None:
        kwargs["result"] = result

    with patched as (m_functional, m_parallel):
        assert (
            aio.core.subprocess.parallel(*args, **kwargs)
            == m_functional.AwaitableGenerator.return_value)

    for k in ["collector", "iterator", "predicate", "result"]:
        kwargs.pop(k, None)

    assert (
        m_functional.AwaitableGenerator.call_args
        == [(m_parallel.return_value, ),
            dict(collector=collector,
                 iterator=iterator,
                 predicate=predicate,
                 result=result)])
    assert (
        m_parallel.call_args
        == [tuple(args), kwargs])
