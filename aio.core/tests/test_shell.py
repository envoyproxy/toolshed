
from unittest.mock import PropertyMock

import pytest

from aio.core import subprocess


@pytest.mark.parametrize(
    "args",
    [[], [f"ARG{i}" for i in range(0, 5)]])
@pytest.mark.parametrize(
    "kwargs",
    [{}, {f"K{i}": f"V{i}" for i in range(0, 5)}])
def test_shell_constructor(patches, args, kwargs):
    patched = patches(
        "subprocess.AAsyncShell.__init__",
        prefix="aio.core.subprocess.shell")

    with patched as (m_super, ):
        m_super.return_value = None
        shell = subprocess.AsyncShell(*args, **kwargs)

    assert isinstance(shell, subprocess.AAsyncShell)
    assert (
        m_super.call_args
        == [tuple(args), kwargs])


@pytest.mark.parametrize(
    "args",
    [[], [f"ARG{i}" for i in range(0, 5)]])
@pytest.mark.parametrize(
    "kwargs",
    [{}, {f"K{i}": f"V{i}" for i in range(0, 5)}])
def test_shell_parallel(patches, args, kwargs):
    shell = subprocess.AsyncShell()
    patched = patches(
        "subprocess.AAsyncShell.parallel",
        prefix="aio.core.subprocess.shell")

    with patched as (m_super, ):
        assert (
            shell.parallel(*args, **kwargs)
            == m_super.return_value)

    assert (
        m_super.call_args
        == [tuple(args), kwargs])


@pytest.mark.parametrize(
    "args",
    [[], [f"ARG{i}" for i in range(0, 5)]])
@pytest.mark.parametrize(
    "kwargs",
    [{}, {f"K{i}": f"V{i}" for i in range(0, 5)}])
async def test_shell_run(patches, args, kwargs):
    shell = subprocess.AsyncShell()
    patched = patches(
        "subprocess.AAsyncShell.run",
        prefix="aio.core.subprocess.shell")

    with patched as (m_super, ):
        assert (
            await shell.run(*args, **kwargs)
            == m_super.return_value)

    assert (
        m_super.call_args
        == [tuple(args), kwargs])


async def test_shell_executor(patches):
    shell = subprocess.AsyncShell()
    patched = patches(
        ("subprocess.AAsyncShell.executor",
         dict(new_callable=PropertyMock)),
        prefix="aio.core.subprocess.shell")

    with patched as (m_super, ):
        assert (
            shell.executor
            == m_super.return_value)

    assert "executor" not in shell.__dict__
