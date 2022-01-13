
from unittest.mock import AsyncMock, MagicMock

import pytest

import aio.subprocess


async def test_subprocess_parallel(patches):
    patched = patches(
        "asyncio",
        "ProcessPoolExecutor",
        ("AsyncSubprocess.run", dict(new_callable=MagicMock)),
        prefix="aio.subprocess.async_subprocess")
    procs = [f"PROC{i}" for i in range(0, 3)]
    kwargs = {f"KEY{i}": f"VALUE{i}" for i in range(0, 3)}

    async def async_result(result):
        return result

    with patched as (m_asyncio, m_future, m_run):
        returned = [f"RESULT{i}" for i in range(0, 5)]
        m_asyncio.as_completed.return_value = [
            async_result(result) for result in returned]

        results = []
        async for result in aio.subprocess.parallel(procs, **kwargs):
            results.append(result)

    assert results == returned
    assert (
        list(m_future.call_args)
        == [(), {}])
    assert (
        list(m_asyncio.as_completed.call_args)
        == [(tuple(
            m_asyncio.ensure_future.return_value
            for i in range(0, len(procs))), ), {}])
    kwargs["executor"] = m_future.return_value.__enter__.return_value
    assert (
        list(list(c) for c in m_run.call_args_list)
        == [[(proc,), kwargs] for proc in procs])
    assert (
        list(list(c) for c in m_asyncio.ensure_future.call_args_list)
        == [[(m_run.return_value,), {}] for proc in procs])


@pytest.mark.parametrize("loop", [True, False])
@pytest.mark.parametrize("executor", [None, "EXECUTOR"])
async def test_subprocess_run(patches, loop, executor):
    patched = patches(
        "asyncio",
        "partial",
        "subprocess",
        prefix="aio.subprocess.async_subprocess")
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
            await aio.subprocess.run(*args, **kwargs)
            == m_loop.run_in_executor.return_value)

    if loop:
        assert not m_asyncio.get_running_loop.called

    kwargs.pop("executor", None)
    kwargs.pop("loop", None)

    assert (
        list(m_partial.call_args)
        == [(m_subproc.run, ) + tuple(args), kwargs])
    assert (
        list(m_loop.run_in_executor.call_args)
        == [(executor, m_partial.return_value), {}])
