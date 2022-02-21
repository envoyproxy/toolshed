
from unittest.mock import MagicMock, PropertyMock

import pytest

import abstracts

from aio.core import event, subprocess


@abstracts.implementer(subprocess.AAsyncShell)
class DummyAsyncShell:

    def parallel(self, *args, **kwargs):
        return super().parallel(*args, **kwargs)

    async def run(self, *args, **kwargs):
        return await super().run(*args, **kwargs)


@pytest.mark.parametrize("fork", [None, True, False])
@pytest.mark.parametrize("raises", [None, True, False])
@pytest.mark.parametrize("handler", [0, None, "HANDLER"])
@pytest.mark.parametrize("loop", [None, False, "LOOP"])
@pytest.mark.parametrize("pool", [None, False, "POOL"])
@pytest.mark.parametrize(
    "kwargs",
    [{}, {f"K{i}": f"V{i}" for i in range(0, 5)}])
def test_shell_constructor(patches, fork, raises, handler, loop, pool, kwargs):
    patched = patches(
        "AAsyncShell.to_list",
        prefix="aio.core.subprocess.abstract.shell")
    shell_kwargs = {}
    if fork is not None:
        shell_kwargs["fork"] = fork
    if raises is not None:
        shell_kwargs["raises"] = raises
    if handler != 0:
        shell_kwargs["handler"] = handler
    if loop is not None:
        shell_kwargs["loop"] = loop
    if pool is not None:
        shell_kwargs["pool"] = pool

    shell_kwargs = {**shell_kwargs, **kwargs}

    with patched as (m_tolist, ):

        with pytest.raises(TypeError):
            subprocess.AAsyncShell(**shell_kwargs)

        shell = DummyAsyncShell(**shell_kwargs)

    assert isinstance(shell, event.IExecutive)
    assert (
        shell._handler
        == (m_tolist
            if handler == 0
            else handler))
    assert (
        shell._fork
        == (True
            if fork is None
            else fork))
    assert shell.fork == shell._fork
    assert "fork" not in shell.__dict__
    assert (
        shell._raises
        == (True
            if raises is None
            else raises))
    assert shell.raises == shell._raises
    assert "raises" not in shell.__dict__
    assert shell._kwargs == kwargs
    assert shell._loop == loop
    assert shell._pool == pool
    assert (
        shell.default_kwargs
        == dict(capture_output=True, encoding="utf-8"))
    assert "default_kwargs" not in shell.__dict__


@pytest.mark.parametrize(
    "args",
    [[], [f"ARG{i}" for i in range(0, 5)]])
@pytest.mark.parametrize(
    "kwargs",
    [{}, {f"K{i}": f"V{i}" for i in range(0, 5)}])
async def test_shell_dunder_call(patches, args, kwargs):
    shell = DummyAsyncShell()
    patched = patches(
        "AAsyncShell.run",
        prefix="aio.core.subprocess.abstract.shell")

    with patched as (m_run, ):
        assert (
            await shell(*args, **kwargs)
            == m_run.return_value)

    assert (
        m_run.call_args
        == [tuple(args), kwargs])


@pytest.mark.parametrize("handler", [None, "HANDLER"])
def test_shell_handler(handler):
    shell = DummyAsyncShell()
    shell._handler = handler
    if handler:
        assert shell.handler == handler
    else:
        assert shell.handler("BOOM") == "BOOM"
    assert "handler" in shell.__dict__


@pytest.mark.parametrize(
    "default_kwargs",
    [{}, {f"DK{i}": f"DV{i}" for i in range(0, 5)}])
@pytest.mark.parametrize(
    "kwargs",
    [{}, {f"K{i}": f"V{i}" for i in range(0, 5)}])
def test_shell_default_kwargs(patches, default_kwargs, kwargs):
    shell = DummyAsyncShell()
    patched = patches(
        ("AAsyncShell.default_kwargs",
         dict(new_callable=PropertyMock)),
        prefix="aio.core.subprocess.abstract.shell")
    shell._kwargs = kwargs

    with patched as (m_defaults, ):
        m_defaults.return_value = default_kwargs
        assert (
            shell.kwargs
            == {**default_kwargs,
                **kwargs})

    assert "kwargs" in shell.__dict__


@pytest.mark.parametrize(
    "args",
    [[], [f"ARG{i}" for i in range(0, 5)]])
@pytest.mark.parametrize(
    "kwargs",
    [{}, {f"K{i}": f"V{i}" for i in range(0, 5)}])
def test_shell_parallel(patches, args, kwargs):
    shell = DummyAsyncShell()
    patched = patches(
        "_parallel",
        "AAsyncShell.parallel_kwargs",
        prefix="aio.core.subprocess.abstract.shell")

    with patched as (m_parallel, m_kwargs):
        m_kwargs.return_value = {
            "PK{i}": "PV{i}" for i in range(0, 5)}
        assert (
            shell.parallel(*args, **kwargs)
            == m_parallel.return_value)

    assert (
        m_parallel.call_args
        == [tuple(args), m_kwargs.return_value])
    assert (
        m_kwargs.call_args
        == [(), kwargs])


@pytest.mark.parametrize(
    "self_kwargs",
    [{}, {f"DK{i}": f"DV{i}" for i in range(0, 5)}])
@pytest.mark.parametrize(
    "kwargs",
    [{}, {f"K{i}": f"V{i}" for i in range(0, 5)}])
@pytest.mark.parametrize(
    "fork", [None, "self", "kwargs"])
def test_shell_parallel_kwargs(patches, self_kwargs, kwargs, fork):
    shell = DummyAsyncShell()
    patched = patches(
        "dict",
        ("AAsyncShell.fork",
         dict(new_callable=PropertyMock)),
        ("AAsyncShell.kwargs",
         dict(new_callable=PropertyMock)),
        prefix="aio.core.subprocess.abstract.shell")
    if fork == "self":
        self_kwargs["fork"] = "SELF"
    if fork == "kwargs":
        kwargs["fork"] = "KWARGS"

    with patched as (m_dict, m_fork, m_kwargs):
        m_dict.return_value = dict(fork="FORK")
        m_kwargs.return_value = self_kwargs
        assert (
            shell.parallel_kwargs(**kwargs)
            == {**dict(fork="FORK"),
                **self_kwargs,
                **kwargs})

    assert (
        m_dict.call_args
        == [(), dict(fork=m_fork.return_value)])


@pytest.mark.parametrize(
    "args",
    [[], [f"ARG{i}" for i in range(0, 5)]])
@pytest.mark.parametrize(
    "kwargs",
    [{}, {f"K{i}": f"V{i}" for i in range(0, 5)}])
async def test_shell_run(patches, args, kwargs):
    shell = DummyAsyncShell()
    patched = patches(
        "_run",
        "AAsyncShell.run_kwargs",
        "AAsyncShell._handle_response",
        prefix="aio.core.subprocess.abstract.shell")
    run_kwargs = {
        "RK{i}": "RV{i}" for i in range(0, 5)}
    run_kwargs["handler"] = "HANDLER"
    run_kwargs["raises"] = "RAISES"

    with patched as (m_run, m_kwargs, m_handle):
        m_kwargs.return_value = run_kwargs
        assert (
            await shell.run(*args, **kwargs)
            == m_handle.return_value)

    assert "handler" not in run_kwargs
    assert "raises" not in run_kwargs
    assert (
        m_handle.call_args
        == [("HANDLER", "RAISES", m_run.return_value), {}])
    assert (
        m_run.call_args
        == [tuple(args), m_kwargs.return_value])
    assert (
        m_kwargs.call_args
        == [(), kwargs])


@pytest.mark.parametrize(
    "self_kwargs",
    [{}, {f"DK{i}": f"DV{i}" for i in range(0, 5)}])
@pytest.mark.parametrize(
    "kwargs",
    [{}, {f"K{i}": f"V{i}" for i in range(0, 5)}])
def test_shell_run_kwargs(patches, self_kwargs, kwargs):
    shell = DummyAsyncShell()
    kwargs = kwargs.copy()
    self_kwargs = self_kwargs.copy()
    patched = patches(
        "dict",
        ("AAsyncShell.handler",
         dict(new_callable=PropertyMock)),
        ("AAsyncShell.kwargs",
         dict(new_callable=PropertyMock)),
        ("AAsyncShell.pool",
         dict(new_callable=PropertyMock)),
        ("AAsyncShell.raises",
         dict(new_callable=PropertyMock)),
        prefix="aio.core.subprocess.abstract.shell")

    with patched as (m_dict, m_handler, m_kwargs, m_pool, m_raises):
        m_dict.return_value = dict(returned="KWARGS")
        m_kwargs.return_value = self_kwargs
        expected = {
            **dict(returned="KWARGS"),
            **self_kwargs,
            **kwargs}
        assert (
            shell.run_kwargs(**kwargs)
            == expected)

    assert (
        m_dict.call_args
        == [(),
            dict(handler=m_handler.return_value,
                 raises=m_raises.return_value,
                 executor=m_pool.return_value)])


def test_shell_to_list():
    shell = DummyAsyncShell()
    response = MagicMock()
    assert (
        shell.to_list(response)
        == response.stdout.split.return_value)
    assert (
        response.stdout.split.call_args
        == [("\n", ), {}])


@pytest.mark.parametrize("stdout", [None, False, "", "STDOUT"])
@pytest.mark.parametrize("stderr", [None, False, "", "STDERR"])
def test_shell__handle_exception(patches, stdout, stderr):
    shell = DummyAsyncShell()
    patched = patches(
        "textwrap",
        prefix="aio.core.subprocess.abstract.shell")
    response = MagicMock()
    response.args = [f"A{i}" for i in range(0, 5)]
    response.stdout = stdout
    response.stderr = stderr
    fail_output = "\n".join(
        out
        for out
        in [response.stdout, response.stderr]
        if out)
    fail_output = f":\n{fail_output}" if fail_output else fail_output

    with patched as (m_wrap, ):
        with pytest.raises(subprocess.exceptions.RunError) as e:
            shell._handle_exception(response)
        assert (
            e.value.args[0]
            == f"Run failed ({m_wrap.shorten.return_value}):{fail_output}")
        assert e.value.args[1] == response

    assert (
        m_wrap.shorten.call_args
        == [(" ".join(response.args), ),
            dict(width=10, placeholder="...")])


@pytest.mark.parametrize("raises", [True, False])
@pytest.mark.parametrize("returncode", range(0, 5))
def test_shell__handle_response(patches, raises, returncode):
    shell = DummyAsyncShell()
    patched = patches(
        "AAsyncShell._handle_exception",
        prefix="aio.core.subprocess.abstract.shell")
    response = MagicMock()
    response.returncode = returncode
    handler = MagicMock()

    with patched as (m_exception, ):
        assert (
            shell._handle_response(handler, raises, response)
            == (m_exception.return_value
                if raises and returncode
                else handler.return_value))

    if raises and returncode:
        assert not handler.called
        assert (
            m_exception.call_args
            == [(response, ), {}])
        return
    assert not m_exception.called
    assert (
        handler.call_args
        == [(response, ), {}])
