
from unittest.mock import PropertyMock

import pytest

from aio.core import output


@pytest.mark.parametrize(
    "args",
    [[], [f"ARG{i}" for i in range(0, 5)]])
@pytest.mark.parametrize(
    "kwargs",
    [{}, {f"K{i}": f"V{i}" for i in range(0, 5)}])
def test_buffered_outputs_constructor(patches, args, kwargs):
    patched = patches(
        "output.ABufferedOutputs.__init__",
        prefix="aio.core.output.output")

    with patched as (m_super, ):
        m_super.return_value = None
        buffered = output.BufferedOutputs(*args, **kwargs)

    assert isinstance(buffered, output.ABufferedOutputs)


@pytest.mark.parametrize("output_class", [None, False, "", "OUTPUT_CLASS"])
def test_buffered_outputs_output_class(output_class):
    buffered = output.BufferedOutputs(
        "HANDLERS", "Q_CLASS", output_class)
    assert (
        buffered.output_class
        == (output_class or output.CapturedOutput))
    assert "output_class" not in buffered.__dict__


@pytest.mark.parametrize("io_class", [None, False, "", "IO_CLASS"])
def test_buffered_outputs_io_class(io_class):
    kwargs = (
        dict(io_class=io_class)
        if io_class is not None
        else {})
    buffered = output.BufferedOutputs(
        "HANDLERS", "Q_CLASS", "OUTPUT_CLASS", **kwargs)
    assert (
        buffered.io_class
        == (io_class or output.QueueIO))
    assert "io_class" not in buffered.__dict__


def test_buffered_outputs_queue_class(patches):
    patched = patches(
        ("output.ABufferedOutputs.queue_class",
         dict(new_callable=PropertyMock)),
        prefix="aio.core.output.output")
    buffered = output.BufferedOutputs(
        "HANDLERS", "Q_CLASS", "OUTPUT_CLASS")

    with patched as (m_super, ):
        assert (
            buffered.queue_class
            == m_super.return_value)

    assert "queue_class" not in buffered.__dict__


@pytest.mark.parametrize(
    "args",
    [[], [f"ARG{i}" for i in range(0, 5)]])
@pytest.mark.parametrize(
    "kwargs",
    [{}, {f"K{i}": f"V{i}" for i in range(0, 5)}])
def test_captured_output_constructor(patches, args, kwargs):
    patched = patches(
        "output.ACapturedOutput.__init__",
        prefix="aio.core.output.output")

    with patched as (m_super, ):
        m_super.return_value = None
        captured = output.CapturedOutput(*args, **kwargs)

    assert isinstance(captured, output.ACapturedOutput)


@pytest.mark.parametrize(
    "args",
    [[], [f"ARG{i}" for i in range(0, 5)]])
@pytest.mark.parametrize(
    "kwargs",
    [{}, {f"K{i}": f"V{i}" for i in range(0, 5)}])
def test_queueio_constructor(patches, args, kwargs):
    patched = patches(
        "output.AQueueIO.__init__",
        prefix="aio.core.output.output")

    with patched as (m_super, ):
        m_super.return_value = None
        queue = output.QueueIO(*args, **kwargs)

    assert isinstance(queue, output.AQueueIO)
