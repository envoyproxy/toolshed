
from unittest.mock import AsyncMock, MagicMock, PropertyMock

import pytest

import abstracts

from aio.core import output


@abstracts.implementer(output.ABufferedOutputs)
class DummyBufferedOutputs:

    @property
    def io_class(self):
        return super().io_class

    @property
    def output_class(self):
        return super().output_class

    @property
    def queue_class(self):
        return super().queue_class


@abstracts.implementer(output.AQueueIO)
class DummyQueueIO:

    @property
    def output_class(self):
        return super().output_class


@pytest.mark.parametrize("encoding", [None, False, "ENCODING"])
def test_captured_output_constructor(encoding):
    kwargs = (
        dict(encoding=encoding)
        if encoding is not None
        else {})
    captured = output.ACapturedOutput("TYPE", "MESSAGE", **kwargs)
    assert captured.type == "TYPE"
    assert captured.message == "MESSAGE"
    assert captured.encoding == (encoding if encoding is not None else "utf-8")


@pytest.mark.parametrize("encoding", [None, "ENCODING"])
def test_captured_output_dunder_str(encoding):
    kwargs = (
        dict(encoding=encoding)
        if encoding is not None
        else {})
    message = MagicMock()
    message.decode.return_value = "  MESSAGE  "
    captured = output.ACapturedOutput("TYPE", message, **kwargs)
    assert (
        str(captured)
        == "MESSAGE")
    assert (
        message.decode.call_args
        == [(encoding or "utf-8", ), {}])


def test_queueio_constructor():

    with pytest.raises(TypeError):
        output.AQueueIO("TYPE", "Q", "OUTPUT_CLASS")

    queue = DummyQueueIO("TYPE", "Q", "OUTPUT_CLASS")
    assert queue.type == "TYPE"
    assert queue.q == "Q"
    assert queue._output_class == "OUTPUT_CLASS"
    assert queue.output_class == "OUTPUT_CLASS"
    assert "output_class" not in queue.__dict__
    assert queue.readable() is False
    assert queue.writable() is True
    assert queue.seekable() is False


def test_queueio_closed():
    q = MagicMock()
    queue = DummyQueueIO("TYPE", q, "OUTPUT_CLASS")
    assert queue.closed == q.closed
    assert "closed" not in queue.__dict__


def test_queueio_write():
    q = MagicMock()
    output_class = MagicMock()
    queue = DummyQueueIO("TYPE", q, output_class)
    assert not queue.write("MESSAGE")
    assert (
        q.put.call_args
        == [(output_class.return_value, ), {}])
    assert (
        output_class.call_args
        == [("TYPE", "MESSAGE"), {}])


@pytest.mark.parametrize("io_class", [None, False, "IO_CLASS"])
def test_buffered_constructor(io_class):
    kwargs = (
        dict(io_class=io_class)
        if io_class is not None
        else {})

    with pytest.raises(TypeError):
        output.ABufferedOutputs(
            "HANDLERS", "Q_CLASS", "OUTPUT_CLASS", **kwargs)

    buffered = DummyBufferedOutputs(
        "HANDLERS", "Q_CLASS", "OUTPUT_CLASS", **kwargs)
    assert buffered.handlers == "HANDLERS"
    assert buffered._queue_class == "Q_CLASS"
    assert buffered._output_class == "OUTPUT_CLASS"
    assert buffered._io_class == io_class
    assert buffered.queue_class == "Q_CLASS"
    assert "queue_class" not in buffered.__dict__
    assert buffered.tasks == []
    assert "tasks" in buffered.__dict__
    iface_props = [
        "io_class", "output_class"]
    for prop in iface_props:
        with pytest.raises(NotImplementedError):
            getattr(buffered, prop)


async def test_buffered_dunder_aenter():
    buffered = DummyBufferedOutputs("HANDLERS", "Q_CLASS", "OUTPUT_CLASS")
    assert await buffered.__aenter__() == buffered


async def test_buffered_dunder_aexit(patches):
    buffered = DummyBufferedOutputs("HANDLERS", "Q_CLASS", "OUTPUT_CLASS")
    patched = patches(
        "ABufferedOutputs.stop_queues",
        "ABufferedOutputs.wait_for_tasks",
        "ABufferedOutputs.close_queues",
        prefix="aio.core.output.abstract.output")

    with patched as (m_stop, m_wait, m_close):
        assert not await buffered.__aexit__("EXC", "EPT", "ION")

    for fun in (m_stop, m_wait, m_close):
        assert (
            fun.call_args
            == [(), {}])


def test_buffered_dunder_getitem(patches):
    buffered = DummyBufferedOutputs("HANDLERS", "Q_CLASS", "OUTPUT_CLASS")
    patched = patches(
        ("ABufferedOutputs.buffers",
         dict(new_callable=PropertyMock)),
        prefix="aio.core.output.abstract.output")

    with patched as (m_buffers, ):
        assert (
            buffered.__getitem__("K")
            == m_buffers.return_value.__getitem__.return_value)

    assert (
        m_buffers.return_value.__getitem__.call_args
        == [("K", ), {}])


def test_buffered_buffers(patches):
    handlers = [f"HANDLER{i}" for i in range(0, 5)]
    buffered = DummyBufferedOutputs(handlers, "Q_CLASS", "OUTPUT_CLASS")
    patched = patches(
        "ABufferedOutputs._io",
        prefix="aio.core.output.abstract.output")

    with patched as (m_io, ):
        assert (
            buffered.buffers
            == {k: m_io.return_value
                for k
                in handlers})

    assert (
        m_io.call_args_list
        == [[(k, ), {}]
            for k
            in handlers])
    assert "buffers" in buffered.__dict__


def test_buffered_loop(patches):
    buffered = DummyBufferedOutputs("HANDLERS", "Q_CLASS", "OUTPUT_CLASS")
    patched = patches(
        "asyncio",
        prefix="aio.core.output.abstract.output")

    with patched as (m_aio, ):
        assert buffered.loop == m_aio.get_running_loop.return_value

    assert (
        m_aio.get_running_loop.call_args
        == [(), {}])
    assert "loop" in buffered.__dict__


def test_buffered_queues(patches):
    handlers = [f"HANDLER{i}" for i in range(0, 5)]
    buffered = DummyBufferedOutputs(handlers, "Q_CLASS", "OUTPUT_CLASS")
    patched = patches(
        ("ABufferedOutputs.queue_class",
         dict(new_callable=PropertyMock)),
        prefix="aio.core.output.abstract.output")

    with patched as (m_class, ):
        assert (
            buffered.queues
            == {k: m_class.return_value.return_value
                for k
                in handlers})

    assert (
        m_class.return_value.call_args_list
        == [[(), {}]
            for k
            in handlers])
    assert "queues" in buffered.__dict__


async def test_buffered_close_queue():
    buffered = DummyBufferedOutputs("HANDLERS", "Q_CLASS", "OUTPUT_CLASS")
    queue = MagicMock()
    queue.wait_closed = AsyncMock()
    assert not await buffered.close_queue(queue)
    assert queue.close.call_args == [(), {}]
    assert queue.wait_closed.call_args == [(), {}]


async def test_buffered_close_queues(patches):
    buffered = DummyBufferedOutputs("HANDLERS", "Q_CLASS", "OUTPUT_CLASS")
    patched = patches(
        "core",
        ("ABufferedOutputs.queues",
         dict(new_callable=PropertyMock)),
        ("ABufferedOutputs.close_queue",
         dict(new_callable=MagicMock)),
        prefix="aio.core.output.abstract.output")
    queues = [f"Q{i}" for i in range(0, 5)]

    with patched as (m_core, m_queues, m_close):
        m_core.tasks.concurrent = AsyncMock()
        m_queues.return_value.values.return_value = queues
        assert not await buffered.close_queues()
        q_iter = m_core.tasks.concurrent.call_args[0][0]
        q_items = list(q_iter)

    assert (
        m_close.call_args_list
        == [[(q, ), {}]
            for q in queues])
    assert (
        q_items
        == [m_close.return_value
            for q
            in queues])
    assert (
        m_queues.return_value.values.call_args
        == [(), {}])
    assert (
        m_core.tasks.concurrent.call_args
        == [(q_iter, ), {}])


@pytest.mark.parametrize("exists", [True, False])
@pytest.mark.parametrize("default", [None, False, "DEFAULT"])
def test_buffered_get(patches, exists, default):
    buffered = DummyBufferedOutputs("HANDLERS", "Q_CLASS", "OUTPUT_CLASS")
    patched = patches(
        ("ABufferedOutputs.buffers",
         dict(new_callable=PropertyMock)),
        prefix="aio.core.output.abstract.output")
    args = (
        (default, )
        if default is not None
        else ())

    with patched as (m_buffers, ):
        m_buffers.return_value.__contains__.return_value = exists
        assert (
            buffered.get("K", *args)
            == (m_buffers.return_value.__getitem__.return_value
                if exists
                else default))

    assert (
        m_buffers.return_value.__contains__.call_args
        == [("K", ), {}])
    if not exists:
        assert not m_buffers.return_value.__getitem__.called
    else:
        assert (
            m_buffers.return_value.__getitem__.call_args
            == [("K", ), {}])


async def test_buffered_stop_queue(patches):
    buffered = DummyBufferedOutputs("HANDLERS", "Q_CLASS", "OUTPUT_CLASS")
    queue = MagicMock()
    queue.put = AsyncMock()
    assert not await buffered.stop_queue(queue)
    assert (
        queue.put.call_args
        == [(output.abstract.output.DEATH_SENTINEL, ), {}])


async def test_buffered_stop_queues(patches):
    buffered = DummyBufferedOutputs("HANDLERS", "Q_CLASS", "OUTPUT_CLASS")
    patched = patches(
        "core",
        ("ABufferedOutputs.queues",
         dict(new_callable=PropertyMock)),
        ("ABufferedOutputs.stop_queue",
         dict(new_callable=MagicMock)),
        prefix="aio.core.output.abstract.output")
    queues = [MagicMock() for i in range(0, 5)]

    with patched as (m_core, m_queues, m_stop):
        m_core.tasks.concurrent = AsyncMock()
        m_queues.return_value.values.return_value = queues
        assert not await buffered.stop_queues()
        q_iter = m_core.tasks.concurrent.call_args[0][0]
        q_items = list(q_iter)

    assert (
        m_stop.call_args_list
        == [[(q.async_q, ), {}]
            for q in queues])
    assert (
        q_items
        == [m_stop.return_value
            for q
            in queues])
    assert (
        m_queues.return_value.values.call_args
        == [(), {}])
    assert (
        m_core.tasks.concurrent.call_args
        == [(q_iter, ), {}])


async def test_buffered_wait_for_tasks(patches):
    buffered = DummyBufferedOutputs("HANDLERS", "Q_CLASS", "OUTPUT_CLASS")
    patched = patches(
        "core",
        ("ABufferedOutputs.tasks",
         dict(new_callable=PropertyMock)),
        prefix="aio.core.output.abstract.output")

    with patched as (m_core, m_tasks):
        m_core.tasks.concurrent = AsyncMock()
        assert not await buffered.wait_for_tasks()

    assert (
        m_core.tasks.concurrent.call_args
        == [(m_tasks.return_value, ), {}])


def test_buffered__io(patches):
    handlers = MagicMock()
    buffered = DummyBufferedOutputs(handlers, "Q_CLASS", "OUTPUT_CLASS")
    patched = patches(
        "io",
        "partial",
        ("ABufferedOutputs.io_class",
         dict(new_callable=PropertyMock)),
        ("ABufferedOutputs.loop",
         dict(new_callable=PropertyMock)),
        ("ABufferedOutputs.output_class",
         dict(new_callable=PropertyMock)),
        ("ABufferedOutputs.queues",
         dict(new_callable=PropertyMock)),
        ("ABufferedOutputs.tasks",
         dict(new_callable=PropertyMock)),
        ("ABufferedOutputs._reader",
         dict(new_callable=MagicMock)),
        prefix="aio.core.output.abstract.output")

    with patched as patchy:
        (m_io, m_partial, m_io_class,
         m_loop, m_out_class, m_queues, m_tasks, m_reader) = patchy
        assert (
            buffered._io("OUTPUT_TYPE")
            == m_io.TextIOWrapper.return_value)

    assert (
        m_queues.return_value.__getitem__.call_args
        == [("OUTPUT_TYPE", ), {}])
    assert (
        handlers.__getitem__.call_args
        == [("OUTPUT_TYPE", ), {}])
    assert (
        m_tasks.return_value.append.call_args
        == [(m_loop.return_value.create_task.return_value, ), {}])
    assert (
        m_loop.return_value.create_task.call_args
        == [(m_reader.return_value, ), {}])
    assert (
        m_reader.call_args
        == [(m_queues.return_value.__getitem__.return_value.async_q,
             handlers.__getitem__.return_value), {}])
    assert (
        m_io.TextIOWrapper.call_args
        == [(m_io_class.return_value.return_value, ),
            dict(write_through=True)])
    assert (
        m_io_class.return_value.call_args
        == [("OUTPUT_TYPE",
             m_queues.return_value.__getitem__.return_value.sync_q,
             m_partial.return_value), {}])
    assert (
        m_partial.call_args
        == [(m_out_class.return_value,
             "OUTPUT_TYPE"), {}])


@pytest.mark.parametrize("gotten", [0, 5, 10])
async def test_buffered__reader(gotten):
    buffered = DummyBufferedOutputs("HANDLERS", "Q_CLASS", "OUTPUT_CLASS")
    queue = MagicMock()
    handler = AsyncMock()
    gotten_items = (
        [f"GET{i}" for i in range(0, gotten)]
        + [output.abstract.output.DEATH_SENTINEL])

    class Getter:
        counter = 0

        async def get(self):
            self.counter += 1
            return gotten_items[self.counter - 1]

    getter = Getter()
    queue.get = AsyncMock(side_effect=getter.get)
    assert not await buffered._reader(queue, handler)
    assert (
        queue.get.call_args_list
        == [[(), {}]
            for g
            in gotten_items])
    assert (
        queue.task_done.call_args_list
        == [[(), {}]
            for g
            in gotten_items])
    assert (
        handler.call_args_list
        == [[(g, ), {}]
            for g
            in gotten_items[:-1]])
