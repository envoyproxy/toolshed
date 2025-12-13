
from unittest.mock import AsyncMock, MagicMock, PropertyMock
import types

import pytest

from aio.run.runner import Runner

from envoy.base import utils


def test_parallelrunner_constructor(iters, patches):
    args = iters(tuple, count=3)
    kwargs = iters(dict, count=3)
    patched = patches(
        "runner.Runner.__init__",
        prefix="envoy.base.utils.parallel_runner")

    with patched as (m_super, ):
        m_super.return_value = None
        runner = utils.ParallelRunner(*args, **kwargs)

    assert isinstance(runner, Runner)
    assert (
        m_super.call_args
        == [args, kwargs])


@pytest.mark.parametrize("prop", ["items"])
def test_parallelrunner_arg_props(patches, prop):
    runner = utils.ParallelRunner()
    patched = patches(
        ("ParallelRunner.args",
         dict(new_callable=PropertyMock)),
        prefix="envoy.base.utils.parallel_runner")

    with patched as (m_args, ):
        assert (
            getattr(runner, prop)
            == getattr(m_args.return_value, prop))

    assert prop not in runner.__dict__


def test_parallelrunner_batch_size(patches):
    runner = utils.ParallelRunner()
    patched = patches(
        "len",
        "math",
        ("ParallelRunner.cpu_count",
         dict(new_callable=PropertyMock)),
        ("ParallelRunner.items",
         dict(new_callable=PropertyMock)),
        prefix="envoy.base.utils.parallel_runner")

    with patched as (m_len, m_math, m_cpu, m_items):
        m_len.return_value = 23
        m_cpu.return_value = 7
        assert runner.batch_size == m_math.ceil.return_value

    assert (
        m_len.call_args
        == [(m_items.return_value, ), {}])
    assert (
        m_math.ceil.call_args
        == [(23 / 7, ), {}])
    assert "batch_size" in runner.__dict__


def test_parallelrunner_batches(iters, patches):
    runner = utils.ParallelRunner()
    patched = patches(
        ("ParallelRunner.batch_size",
         dict(new_callable=PropertyMock)),
        ("ParallelRunner.cpu_count",
         dict(new_callable=PropertyMock)),
        ("ParallelRunner.items",
         dict(new_callable=PropertyMock)),
        prefix="envoy.base.utils.parallel_runner")
    items = iters(count=7)
    expected = [
        items[:3],
        items[3:6],
        items[6:7]]

    with patched as (m_batch, m_cpu_count, m_items):
        m_cpu_count.return_value = 4
        m_batch.return_value = 3
        m_items.return_value = items
        resultgen = runner.batches
        assert list(resultgen) == expected

    assert isinstance(resultgen, types.GeneratorType)

    assert "batches" not in runner.__dict__


@pytest.mark.parametrize("count", [None, "", 23, "COUNT"])
def test_parallelrunner_cpu_count(patches, count):
    runner = utils.ParallelRunner()
    patched = patches(
        "os",
        prefix="envoy.base.utils.parallel_runner")

    with patched as (m_os, ):
        m_os.cpu_count.return_value = count
        assert runner.cpu_count == (count or 1)

    assert "cpu_count" in runner.__dict__


def test_projecrunner_add_arguments(patches):
    runner = utils.ParallelRunner()
    parser = MagicMock()
    patched = patches(
        "runner.Runner.add_arguments",
        prefix="envoy.base.utils.parallel_runner")

    with patched as (m_super, ):
        runner.add_arguments(parser)

    assert (
        m_super.call_args
        == [(parser, ), {}])
    assert (
        parser.add_argument.call_args_list
        == [[('command',), dict(type=str)],
            [('items',), dict(nargs="+")]])


def test_parallelrunner_command(iters, patches):
    runner = utils.ParallelRunner()
    patched = patches(
        ("ParallelRunner.args",
         dict(new_callable=PropertyMock)),
        prefix="envoy.base.utils.parallel_runner")
    command = "FOO BAR BAZ"
    batch = iters()
    extra = " ".join(batch)

    with patched as (m_args, ):
        m_args.return_value.command = command
        assert (
            runner.command(batch)
            == f"{command} {extra}")


@pytest.mark.parametrize("lines", [0, 3, 7])
def test_parallelrunner_handle_result(iters, patches, lines):
    runner = utils.ParallelRunner()
    patched = patches(
        ("ParallelRunner.log",
         dict(new_callable=PropertyMock)),
        prefix="envoy.base.utils.parallel_runner")
    lines = iters(count=lines)
    cmd = MagicMock()
    result = "\n > ".join(lines)
    result = f"\n > {result}" if result else ""

    with patched as (m_log, ):
        assert not runner.handle_result(cmd, lines)

    assert (
        m_log.return_value.success.call_args
        == [(f"{cmd}{result}", ), {}])


async def test_parallelrunner_run(iters, patches):
    runner = utils.ParallelRunner()
    patched = patches(
        "asyncio",
        ("ParallelRunner.batches",
         dict(new_callable=PropertyMock)),
        "ParallelRunner.command",
        "ParallelRunner.handle_result",
        ("ParallelRunner._run",
         dict(new_callable=MagicMock)),
        prefix="envoy.base.utils.parallel_runner")
    batches = iters()
    results = iters(cb=lambda i: (f"CMD{i}", f"LINES{i}"))

    with patched as (m_asyncio, m_batches, m_command, m_handle, m_run):
        m_batches.return_value = batches
        m_asyncio.gather.side_effect = AsyncMock(return_value=results)
        assert not await runner.run()

    assert (
        m_command.call_args_list
        == [[(batch, ), {}]
            for batch
            in batches])
    assert (
        m_run.call_args_list
        == [[(m_command.return_value, ), {}]
            for batch
            in batches])
    assert (
        m_handle.call_args_list
        == [[result, {}]
            for result
            in results])


@pytest.mark.parametrize("stderr", [True, False])
async def test_parallelrunner__run(iters, patches, stderr):
    runner = utils.ParallelRunner()
    patched = patches(
        "asyncio",
        ("ParallelRunner.log",
         dict(new_callable=PropertyMock)),
        prefix="envoy.base.utils.parallel_runner")
    _stdout = iters()
    stdout = MagicMock()
    stdout.decode.return_value.split.return_value = _stdout + ["", None]
    stderr = MagicMock() if stderr else None
    cmd = MagicMock()

    with patched as (m_asyncio, m_log):
        shell = AsyncMock()
        m_asyncio.create_subprocess_shell.side_effect = shell
        shell.return_value.communicate.side_effect = AsyncMock(
            return_value=[stdout, stderr])
        assert (
            await runner._run(cmd)
            == (cmd, _stdout))

    assert (
        shell.call_args
        == [(cmd, ),
            dict(stdout=m_asyncio.subprocess.PIPE,
                 stderr=m_asyncio.subprocess.PIPE)])

    if stderr:
        assert (
            m_log.return_value.warning.call_args
            == [(f'({cmd})\n{stderr.decode.return_value}', ), {}])
    else:
        assert not m_log.called
    assert (
        stdout.decode.call_args
        == [(), {}])
    assert (
        stdout.decode.return_value.split.call_args
        == [("\n", ), {}])
