
from unittest.mock import MagicMock, PropertyMock

import pytest

import abstracts

from aio.core import subprocess


@abstracts.implementer(subprocess.ISubprocessHandler)
class DummySubprocessHandlerInterface:

    @property
    def encoding(self):
        return subprocess.ISubprocessHandler.encoding.fget(self)

    @property
    def args(self):
        return subprocess.ISubprocessHandler.args.fget(self)

    @property
    def kwargs(self):
        return subprocess.ISubprocessHandler.kwargs.fget(self)

    @property
    def in_directory(self):
        return subprocess.ISubprocessHandler.in_directory.fget(self)

    @property
    def path(self):
        return subprocess.ISubprocessHandler.path.fget(self)

    def handle(self, response):
        return subprocess.ISubprocessHandler.handle(self, response)

    def handle_error(self, response):
        return subprocess.ISubprocessHandler.handle_error(self, response)

    def handle_response(self, response):
        return subprocess.ISubprocessHandler.handle_response(self, response)

    def has_failed(self, response):
        return subprocess.ISubprocessHandler.has_failed(self, response)

    def run(self, *args, **kwargs):
        return subprocess.ISubprocessHandler.run(self, *args, **kwargs)

    def run_subprocess(self, *args, **kwargs):
        return subprocess.ISubprocessHandler.run_subprocess(
            self, *args, **kwargs)

    def subprocess_args(self, *args):
        return subprocess.ISubprocessHandler.subprocess_args(self, *args)

    def subprocess_kwargs(self, **kwargs):
        return subprocess.ISubprocessHandler.subprocess_kwargs(self, **kwargs)


def test_subprocess_handler_interface():
    with pytest.raises(TypeError):
        subprocess.ISubprocessHandler()

    iface = DummySubprocessHandlerInterface()
    iface_props = [
        "encoding", "args", "kwargs", "path", "in_directory"]
    for iface_prop in iface_props:
        with pytest.raises(NotImplementedError):
            getattr(iface, iface_prop)
    response_methods = [
        "handle", "handle_error", "handle_response", "has_failed"]
    for response_method in response_methods:
        with pytest.raises(NotImplementedError):
            getattr(iface, response_method)("RESPONSE")
    subproc_methods = [
        "run", "run_subprocess"]
    for subproc_method in subproc_methods:
        with pytest.raises(NotImplementedError):
            getattr(iface, subproc_method)("SUBPROC", "ARG", KW="VALUE")
    with pytest.raises(NotImplementedError):
        iface.subprocess_args("SUBPROC", "ARG")
    with pytest.raises(NotImplementedError):
        iface.subprocess_kwargs(KW="VALUE")


@abstracts.implementer(subprocess.ASubprocessHandler)
class DummySubprocessHandler:

    def handle(self, response):
        return super().handle(response)

    def handle_error(self, response):
        return super().handle_error(response)


@pytest.mark.parametrize("encoding", [None, "", "ENCODING"])
@pytest.mark.parametrize(
    "args",
    [[], [f"ARG{i}" for i in range(0, 5)]])
@pytest.mark.parametrize(
    "kwargs",
    [{}, {f"K{i}": f"V{i}" for i in range(0, 5)}])
def test_subprocess_handler_constructor(patches, encoding, args, kwargs):
    if encoding is not None:
        kwargs["encoding"] = encoding

    patched = patches(
        "directory.ADirectoryContext.__init__",
        prefix="aio.core.subprocess.handler")

    with patched as (m_super, ):
        m_super.return_value = None
        handler = DummySubprocessHandler("PATH", *args, **kwargs)

    encoding = kwargs.pop("encoding", "utf-8")
    assert (
        m_super.call_args
        == [(handler, "PATH"), {}])
    assert handler._encoding == encoding
    assert handler._args == tuple(args or [])
    assert handler._kwargs == kwargs
    assert handler.encoding == encoding
    assert "encoding" not in handler.__dict__
    assert handler.args == tuple(args or [])
    assert "args" not in handler.__dict__


def test_subprocess_handler_dunder_call(patches):
    handler = DummySubprocessHandler("PATH")
    patched = patches(
        "ASubprocessHandler.run",
        prefix="aio.core.subprocess.handler")
    args = [f"ARG{i}" for i in range(0, 5)]

    with patched as (m_run, ):
        assert (
            handler(*args)
            == m_run.return_value)

    assert (
        m_run.call_args
        == [tuple(args), {}])


def test_subprocess_handler_dunder_str():
    handler = DummySubprocessHandler("PATH")
    assert (
        str(handler)
        == f"{handler.__class__.__module__}.{handler.__class__.__name__}")


def test_subprocess_handler_kwargs(patches):
    handler = DummySubprocessHandler("PATH")
    patched = patches(
        "dict",
        ("ASubprocessHandler.encoding",
         dict(new_callable=PropertyMock)),
        ("ASubprocessHandler.path",
         dict(new_callable=PropertyMock)),
        prefix="aio.core.subprocess.handler")

    with patched as (m_dict, m_enc, m_path):
        assert (
            handler.kwargs
            == m_dict.return_value)

    assert (
        m_dict.call_args
        == [(),
            dict(cwd=m_path.return_value,
                 capture_output=True,
                 encoding=m_enc.return_value)])
    assert "kwargs" not in handler.__dict__


def test_subprocess_handler_log(patches):
    handler = DummySubprocessHandler("PATH")
    patched = patches(
        "logging",
        "str",
        prefix="aio.core.subprocess.handler")

    with patched as (m_logging, m_str):
        assert (
            handler.log
            == m_logging.getLogger.return_value)

    assert (
        m_logging.getLogger.call_args
        == [(m_str.return_value, ), {}])
    assert (
        m_str.call_args
        == [(handler, ), {}])
    assert "log" in handler.__dict__


@pytest.mark.parametrize(
    "handle",
    [["handle", "RESPONSE"], ["handle_error", "ERROR"]])
def test_subprocess_handler_handles(patches, handle):
    handle_method, key = handle
    handler = DummySubprocessHandler("PATH")
    patched = patches(
        "dict",
        prefix="aio.core.subprocess.handler")
    response = MagicMock()

    with patched as (m_dict, ):
        assert (
            getattr(handler, handle_method)(response)
            == m_dict.return_value)

    assert (
        m_dict.call_args
        == [(),
            {key:
             [response.returncode,
              response.stdout,
              response.stderr]}])


@pytest.mark.parametrize("has_failed", [True, False])
def test_subprocess_handler_handle_response(patches, has_failed):
    handler = DummySubprocessHandler("PATH")
    patched = patches(
        "ASubprocessHandler.has_failed",
        "ASubprocessHandler.handle",
        "ASubprocessHandler.handle_error",
        prefix="aio.core.subprocess.handler")
    response = MagicMock()

    with patched as (m_failed, m_handle, m_error):
        m_failed.return_value = has_failed
        assert (
            handler.handle_response(response)
            == (m_handle.return_value
                if not has_failed
                else m_error.return_value))

    assert (
        m_failed.call_args
        == [(response, ), {}])
    if not has_failed:
        assert not m_error.called
        assert (
            m_handle.call_args
            == [(response, ), {}])
        return
    assert not m_handle.called
    assert (
        m_error.call_args
        == [(response, ), {}])


def test_subprocess_handler_has_failed(patches):
    handler = DummySubprocessHandler("PATH")
    patched = patches(
        "bool",
        prefix="aio.core.subprocess.handler")
    response = MagicMock()

    with patched as (m_bool, ):
        assert (
            handler.has_failed(response)
            == m_bool.return_value)

    assert (
        m_bool.call_args
        == [(response.returncode, ), {}])


def test_subprocess_handler_run(patches):
    handler = DummySubprocessHandler("PATH")
    patched = patches(
        "ASubprocessHandler.handle_response",
        "ASubprocessHandler.run_subprocess",
        "ASubprocessHandler.subprocess_args",
        "ASubprocessHandler.subprocess_kwargs",
        prefix="aio.core.subprocess.handler")
    args = [f"ARG{i}" for i in range(0, 5)]
    kwargs = {f"K{i}": f"V{i}" for i in range(0, 5)}

    with patched as (m_handle, m_run, m_args, m_kwargs):
        m_args.side_effect = lambda *la: la
        m_kwargs.side_effect = lambda **kwa: kwa
        assert (
            handler.run(*args, **kwargs)
            == m_handle.return_value)

    assert (
        m_handle.call_args
        == [(m_run.return_value, ), {}])
    assert (
        m_run.call_args
        == [tuple(args), kwargs])
    assert (
        m_args.call_args
        == [tuple(args), {}])
    assert (
        m_kwargs.call_args
        == [(), kwargs])


def test_subprocess_handler_run_subprocess(patches):
    handler = DummySubprocessHandler("PATH")
    patched = patches(
        "subprocess",
        prefix="aio.core.subprocess.handler")
    args = [f"ARG{i}" for i in range(0, 5)]
    kwargs = {f"K{i}": f"V{i}" for i in range(0, 5)}

    with patched as (m_subproc, ):
        assert (
            handler.run_subprocess(*args, **kwargs)
            == m_subproc.run.return_value)

    assert (
        m_subproc.run.call_args
        == [tuple(args), kwargs])


def test_subprocess_handler_subprocess_args(patches):
    handler = DummySubprocessHandler("PATH")
    patched = patches(
        ("ASubprocessHandler.args",
         dict(new_callable=PropertyMock)),
        prefix="aio.core.subprocess.handler")
    args = [f"ARG{i}" for i in range(3, 10)]
    self_args = [f"ARG{i}" for i in range(0, 7)]
    expected = ((*self_args, *args), )

    with patched as (m_args, ):
        m_args.return_value = self_args
        assert (
            handler.subprocess_args(*args)
            == expected)


def test_subprocess_handler_subprocess_kwargs(patches):
    handler = DummySubprocessHandler("PATH")
    patched = patches(
        ("ASubprocessHandler.kwargs",
         dict(new_callable=PropertyMock)),
        prefix="aio.core.subprocess.handler")
    kwargs = {f"K{i}": f"V2{i}" for i in range(3, 10)}
    self_kwargs = {f"K{i}": f"V1{i}" for i in range(0, 7)}
    expected = self_kwargs.copy()
    expected.update(kwargs)

    with patched as (m_kwargs, ):
        m_kwargs.return_value = self_kwargs
        assert (
            handler.subprocess_kwargs(**kwargs)
            == expected)
