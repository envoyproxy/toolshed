
import sys
from unittest.mock import AsyncMock, MagicMock, PropertyMock

import pytest

from aio.core import pipe


class DummyProcessProtocol(pipe.AProcessProtocol):
    _do_process = False

    async def process(self, request):
        if self._do_process:
            return await super().process(request)
        return await pipe.AProcessProtocol.process.__wrapped__(self, request)


async def test_processprotocol_constructor():
    with pytest.raises(TypeError):
        pipe.AProcessProtocol("PROCESSOR", "ARGS")

    protocol = DummyProcessProtocol("PROCESSOR", "ARGS")
    assert protocol.processor == "PROCESSOR"
    assert protocol.args == "ARGS"

    with pytest.raises(NotImplementedError):
        await protocol.process("REQUEST")


async def test_processprotocol_dunder_call(patches):
    protocol = DummyProcessProtocol("PROCESSOR", "ARGS")
    protocol._do_process = True
    patched = patches(
        ("AProcessProtocol.process",
         dict(new_callable=AsyncMock)),
        prefix="aio.core.pipe.abstract.pipe")
    request = MagicMock()

    with patched as (m_proc, ):
        assert (
            await protocol.__call__(request)
            == m_proc.return_value)

    assert (
        m_proc.call_args
        == [(request, ), {}])


@pytest.mark.parametrize("log", [None, "", (), "LOG"])
@pytest.mark.parametrize("stdin", [True, False])
@pytest.mark.parametrize("stdout", [True, False])
def test_stdinstdoutprocessor_constructor(log, stdin, stdout):
    kwargs = {}
    if log is not None:
        kwargs["log"] = log
    if stdin:
        kwargs["stdin"] = MagicMock()
    if stdout:
        kwargs["stdout"] = MagicMock()

    processor = pipe.AStdinStdoutProcessor("PROTOCOL", **kwargs)
    assert processor._protocol == "PROTOCOL"
    assert processor.stdin == kwargs.get("stdin", sys.stdin)
    assert processor.stdout == kwargs.get("stdout", sys.stdout)


async def test_stdinstdoutprocessor_dunder_call(patches):
    processor = pipe.AStdinStdoutProcessor("PROTOCOL")
    patched = patches(
        ("AStdinStdoutProcessor.start",
         dict(new_callable=AsyncMock)),
        prefix="aio.core.pipe.abstract.pipe")

    with patched as (m_start, ):
        assert not await processor.__call__()

    assert (
        m_start.call_args
        == [(), {}])


def test_stdinstdoutprocessor_connecting(patches):
    processor = pipe.AStdinStdoutProcessor("PROTOCOL")
    patched = patches(
        "asyncio",
        prefix="aio.core.pipe.abstract.pipe")

    with patched as (m_asyncio, ):
        assert processor.connecting == m_asyncio.Lock.return_value

    assert (
        m_asyncio.Lock.call_args
        == [(), {}])
    assert "connecting" in processor.__dict__


async def test_stdinstdoutprocessor_connection(patches):
    processor = pipe.AStdinStdoutProcessor("PROTOCOL")
    patched = patches(
        ("AStdinStdoutProcessor.loop",
         dict(new_callable=PropertyMock)),
        ("AStdinStdoutProcessor.stream_reader",
         dict(new_callable=PropertyMock)),
        ("AStdinStdoutProcessor.stream_protocol",
         dict(new_callable=PropertyMock)),
        ("AStdinStdoutProcessor.stream_writer",
         dict(new_callable=PropertyMock)),
        prefix="aio.core.pipe.abstract.pipe")

    with patched as (m_loop, m_read, m_proto, m_write):
        write = AsyncMock()
        m_write.side_effect = write
        m_loop.return_value.connect_read_pipe = AsyncMock()
        assert (
            await processor.connection
            == (m_read.return_value, write.return_value)
            == getattr(
                processor,
                pipe.AStdinStdoutProcessor.connection.cache_name)[
                    "connection"])
        lam = m_loop.return_value.connect_read_pipe.call_args[0][0]
        assert lam() == m_proto.return_value

    assert (
        m_loop.return_value.connect_read_pipe.call_args
        == [(lam, sys.stdin), {}])


def test_stdinstdoutprocessor_in_q(patches):
    processor = pipe.AStdinStdoutProcessor("PROTOCOL")
    patched = patches(
        "asyncio",
        prefix="aio.core.pipe.abstract.pipe")

    with patched as (m_asyncio, ):
        assert processor.in_q == m_asyncio.Queue.return_value

    assert (
        m_asyncio.Queue.call_args
        == [(), {}])
    assert "in_q" in processor.__dict__


async def test_stdinstdoutprocessor_listener(iters, patches):
    processor = pipe.AStdinStdoutProcessor("PROTOCOL")
    patched = patches(
        ("AStdinStdoutProcessor.connecting",
         dict(new_callable=PropertyMock)),
        ("AStdinStdoutProcessor.in_q",
         dict(new_callable=PropertyMock)),
        ("AStdinStdoutProcessor.reader",
         dict(new_callable=PropertyMock)),
        "AStdinStdoutProcessor.log",
        prefix="aio.core.pipe.abstract.pipe")
    lines = iters(count=20, cb=lambda i: MagicMock())
    lines[7] = " "
    lines[13] = "\n"
    lines[17] = ""
    counter = MagicMock()
    counter.i = 0

    async def readline():
        counter.i += 1
        return lines[counter.i - 1]

    with patched as (m_connect, m_in_q, m_read, m_log):
        connect = AsyncMock()
        m_connect.return_value.__aenter__ = connect
        reader = AsyncMock()
        reader.return_value.readline = AsyncMock(
            side_effect=readline)
        m_read.side_effect = reader
        m_in_q.return_value.put = AsyncMock()
        assert not await processor.listener

    assert not hasattr(
        processor,
        pipe.AStdinStdoutProcessor.listener.cache_name)
    assert connect.called
    assert (
        m_log.call_args_list
        == [[(f"START LISTENING {reader.return_value}", ),
             {}],
            [("STOP LISTENING", ), {}]])
    assert (
        reader.return_value.readline.call_args_list
        == [[(), {}]] * 18)
    assert (
        m_in_q.return_value.put.call_args_list
        == ([[(m.decode.return_value, ), {}]
             for i, m
             in enumerate(lines)
             if m.strip()
             and i < 18]
            + [[("", ), {}]]))
    for i, line in enumerate(lines):
        if line.strip() and i < 18:
            assert (
                line.decode.call_args
                == [(), {}])


def test_stdinstdoutprocessor_loop(patches):
    processor = pipe.AStdinStdoutProcessor("PROTOCOL")
    patched = patches(
        "asyncio",
        prefix="aio.core.pipe.abstract.pipe")

    with patched as (m_asyncio, ):
        assert processor.loop == m_asyncio.get_event_loop.return_value

    assert (
        m_asyncio.get_event_loop.call_args
        == [(), {}])
    assert "loop" in processor.__dict__


def test_stdinstdoutprocessor_out_q(patches):
    processor = pipe.AStdinStdoutProcessor("PROTOCOL")
    patched = patches(
        "asyncio",
        prefix="aio.core.pipe.abstract.pipe")

    with patched as (m_asyncio, ):
        assert processor.out_q == m_asyncio.Queue.return_value

    assert (
        m_asyncio.Queue.call_args
        == [(), {}])
    assert "out_q" in processor.__dict__


async def test_stdinstdoutprocessor_processor(iters, patches):
    processor = pipe.AStdinStdoutProcessor("PROTOCOL")
    patched = patches(
        ("AStdinStdoutProcessor.connecting",
         dict(new_callable=PropertyMock)),
        ("AStdinStdoutProcessor.protocol",
         dict(new_callable=PropertyMock)),
        "AStdinStdoutProcessor.complete",
        "AStdinStdoutProcessor.log",
        "AStdinStdoutProcessor.process",
        "AStdinStdoutProcessor.recv",
        "AStdinStdoutProcessor.send",
        prefix="aio.core.pipe.abstract.pipe")
    lines = iters(count=20, cb=lambda i: MagicMock())
    lines[17] = ""
    counter = MagicMock()
    counter.i = 0

    async def recv():
        counter.i += 1
        return lines[counter.i - 1]

    with patched as patchy:
        (m_connect, m_proto, m_complete,
         m_log, m_process, m_recv, m_send) = patchy
        connect = AsyncMock()
        m_connect.return_value.__aenter__ = connect
        proto = AsyncMock()
        m_proto.side_effect = proto
        m_recv.side_effect = AsyncMock(side_effect=recv)
        assert not await processor.processor

    assert not hasattr(
        processor,
        pipe.AStdinStdoutProcessor.processor.cache_name)
    assert connect.called
    assert (
        m_log.call_args_list
        == [[(f"START PROCESSING {proto.return_value}", ), {}],
            [("STOP PROCESSING", ), {}]])
    assert (
        m_recv.call_args_list
        == [[(), {}]] * 18)
    assert (
        m_send.call_args_list
        == ([[(m_process.return_value, ), {}]
             for i, m
             in enumerate(lines)
             if i < 17]
            + [[("", ), {}]]))
    assert (
        m_process.call_args_list
        == ([[(m, ), {}]
             for i, m
             in enumerate(lines)
             if i < 17]))
    assert (
        m_complete.call_args_list
        == ([[(), {}]
             for i, m
             in enumerate(lines)
             if i < 17]))


async def test_stdinstdoutprocessor_protocol():
    protocol = AsyncMock()
    processor = pipe.AStdinStdoutProcessor(protocol)
    assert (
        await processor.protocol
        == protocol.return_value
        == getattr(
            processor,
            pipe.AStdinStdoutProcessor.protocol.cache_name)[
                "protocol"])

    assert (
        protocol.call_args
        == [(processor, ), {}])


async def test_stdinstdoutprocessor_reader(patches):
    processor = pipe.AStdinStdoutProcessor("PROTOCOL")
    patched = patches(
        ("AStdinStdoutProcessor.connection",
         dict(new_callable=PropertyMock)),
        prefix="aio.core.pipe.abstract.pipe")

    with patched as (m_connect, ):
        connect = AsyncMock()
        m_connect.side_effect = connect
        assert (
            await processor.reader
            == connect.return_value.__getitem__.return_value)

    assert not hasattr(
        processor,
        pipe.AStdinStdoutProcessor.reader.cache_name)
    assert (
        connect.return_value.__getitem__.call_args
        == [(0, ), {}])


async def test_stdinstdoutprocessor_sender(iters, patches):
    processor = pipe.AStdinStdoutProcessor("PROTOCOL")
    patched = patches(
        ("AStdinStdoutProcessor.connecting",
         dict(new_callable=PropertyMock)),
        ("AStdinStdoutProcessor.out_q",
         dict(new_callable=PropertyMock)),
        ("AStdinStdoutProcessor.writer",
         dict(new_callable=PropertyMock)),
        "AStdinStdoutProcessor.log",
        prefix="aio.core.pipe.abstract.pipe")
    lines = iters(count=20, cb=lambda i: MagicMock())
    lines[17] = ""
    counter = MagicMock()
    counter.i = 0

    async def get():
        counter.i += 1
        return lines[counter.i - 1]

    with patched as (m_connect, m_out_q, m_writer, m_log):
        connect = AsyncMock()
        m_connect.return_value.__aenter__ = connect
        writer = AsyncMock()
        write = MagicMock()
        writer.return_value.write = write
        m_writer.side_effect = writer
        m_out_q.return_value.get.side_effect = AsyncMock(side_effect=get)
        assert not await processor.sender

    assert not hasattr(
        processor,
        pipe.AStdinStdoutProcessor.sender.cache_name)
    assert connect.called
    assert (
        m_log.call_args_list
        == [[(f"START SENDING {writer.return_value}", ), {}],
            [("STOP SENDING", ), {}]])
    assert (
        m_out_q.return_value.get.call_args_list
        == [[(), {}]] * 18)
    assert (
        m_out_q.return_value.task_done.call_args_list
        == [[(), {}]] * 17)
    assert (
        write.call_args_list
        == ([[(m.encode.return_value, ), {}]
             for i, m
             in enumerate(lines)
             if i < 17]))
    for i, line in enumerate(lines):
        if i < 17:
            assert (
                line.encode.call_args
                == [(), {}])


def test_stdinstdoutprocessor_stream_protocol(patches):
    processor = pipe.AStdinStdoutProcessor("PROTOCOL")
    patched = patches(
        "asyncio",
        ("AStdinStdoutProcessor.stream_reader",
         dict(new_callable=PropertyMock)),
        prefix="aio.core.pipe.abstract.pipe")

    with patched as (m_asyncio, m_reader):
        assert (
            processor.stream_protocol
            == m_asyncio.StreamReaderProtocol.return_value)

    assert (
        m_asyncio.StreamReaderProtocol.call_args
        == [(m_reader.return_value, ), {}])
    assert "stream_protocol" in processor.__dict__


def test_stdinstdoutprocessor_stream_reader(patches):
    processor = pipe.AStdinStdoutProcessor("PROTOCOL")
    patched = patches(
        "asyncio",
        prefix="aio.core.pipe.abstract.pipe")

    with patched as (m_asyncio, ):
        assert processor.stream_reader == m_asyncio.StreamReader.return_value

    assert (
        m_asyncio.StreamReader.call_args
        == [(), {}])
    assert "stream_reader" in processor.__dict__


async def test_stdinstdoutprocessor_stream_transport(patches):
    processor = pipe.AStdinStdoutProcessor("PROTOCOL")
    patched = patches(
        "asyncio",
        ("AStdinStdoutProcessor.loop",
         dict(new_callable=PropertyMock)),
        prefix="aio.core.pipe.abstract.pipe")

    with patched as (m_asyncio, m_loop):
        m_loop.return_value.connect_write_pipe = AsyncMock()
        assert (
            await processor.stream_transport
            == m_loop.return_value.connect_write_pipe.return_value
            == getattr(
                processor,
                pipe.AStdinStdoutProcessor.stream_transport.cache_name)[
                    "stream_transport"])

    assert (
        m_loop.return_value.connect_write_pipe.call_args
        == [(m_asyncio.streams.FlowControlMixin, sys.stdout), {}])


async def test_stdinstdoutprocessor_stream_writer(patches):
    processor = pipe.AStdinStdoutProcessor("PROTOCOL")
    patched = patches(
        "asyncio",
        ("AStdinStdoutProcessor.loop",
         dict(new_callable=PropertyMock)),
        ("AStdinStdoutProcessor.stream_reader",
         dict(new_callable=PropertyMock)),
        ("AStdinStdoutProcessor.stream_transport",
         dict(new_callable=PropertyMock)),
        prefix="aio.core.pipe.abstract.pipe")
    transport, flow = MagicMock(), MagicMock()

    with patched as (m_asyncio, m_loop, m_read, m_tport):
        transporter = AsyncMock(return_value=(transport, flow))
        m_tport.side_effect = transporter
        assert (
            await processor.stream_writer
            == m_asyncio.StreamWriter.return_value
            == getattr(
                processor,
                pipe.AStdinStdoutProcessor.stream_writer.cache_name)[
                    "stream_writer"])

    assert (
        m_asyncio.StreamWriter.call_args
        == [(transport, flow, m_read.return_value, m_loop.return_value), {}])


async def test_stdinstdoutprocessor_writer(patches):
    processor = pipe.AStdinStdoutProcessor("PROTOCOL")
    patched = patches(
        ("AStdinStdoutProcessor.connection",
         dict(new_callable=PropertyMock)),
        prefix="aio.core.pipe.abstract.pipe")

    with patched as (m_connect, ):
        connect = AsyncMock()
        m_connect.side_effect = connect
        assert (
            await processor.writer
            == connect.return_value.__getitem__.return_value)

    assert not hasattr(
        processor,
        pipe.AStdinStdoutProcessor.writer.cache_name)
    assert (
        connect.return_value.__getitem__.call_args
        == [(1, ), {}])


def test_stdinstdoutprocessor_complete(patches):
    processor = pipe.AStdinStdoutProcessor("PROTOCOL")
    patched = patches(
        "asyncio",
        ("AStdinStdoutProcessor.in_q",
         dict(new_callable=PropertyMock)),
        prefix="aio.core.pipe.abstract.pipe")

    with patched as (m_asyncio, m_in_q):
        assert not processor.complete()

    assert (
        m_in_q.return_value.task_done.call_args
        == [(), {}])


@pytest.mark.parametrize("log", [None, MagicMock()])
def test_stdinstdoutprocessor_log(log):
    processor = pipe.AStdinStdoutProcessor("PROCESSOR", "ARGS", log=log)
    message = MagicMock()
    assert not processor.log(message)
    if log:
        assert (
            log.call_args
            == [(f"{message}\n", ), {}])


async def test_stdinstdoutprocessor_process(patches):
    processor = pipe.AStdinStdoutProcessor("PROTOCOL")
    patched = patches(
        ("AStdinStdoutProcessor.protocol",
         dict(new_callable=PropertyMock)),
        "AStdinStdoutProcessor.log",
        prefix="aio.core.pipe.abstract.pipe")
    data = MagicMock()

    with patched as (m_protocol, m_log):
        protocol = AsyncMock()
        m_protocol.side_effect = protocol
        assert (
            await processor.process(data)
            == protocol.return_value.return_value)

    assert (
        m_log.call_args
        == [(f"PROCESS: {protocol.return_value} {data}", ),
            {}])
    assert (
        protocol.return_value.call_args
        == [(data, ), {}])


async def test_stdinstdoutprocessor_recv(patches):
    processor = pipe.AStdinStdoutProcessor("PROTOCOL")
    patched = patches(
        ("AStdinStdoutProcessor.in_q",
         dict(new_callable=PropertyMock)),
        "AStdinStdoutProcessor.log",
        prefix="aio.core.pipe.abstract.pipe")

    with patched as (m_in_q, m_log):
        m_in_q.return_value.get = AsyncMock()
        assert (
            await processor.recv()
            == m_in_q.return_value.get.return_value)

    assert (
        m_log.call_args
        == [(f"RECV: {m_in_q.return_value.get.return_value}", ),
            {}])
    assert (
        m_in_q.return_value.get.call_args
        == [(), {}])


async def test_stdinstdoutprocessor_send(patches):
    processor = pipe.AStdinStdoutProcessor("PROTOCOL")
    patched = patches(
        ("AStdinStdoutProcessor.out_q",
         dict(new_callable=PropertyMock)),
        "AStdinStdoutProcessor.log",
        prefix="aio.core.pipe.abstract.pipe")
    msg = MagicMock()

    with patched as (m_out_q, m_log):
        m_out_q.return_value.put = AsyncMock()
        assert not await processor.send(msg)

    assert (
        m_log.call_args
        == [(f"SEND: {msg}", ),
            {}])
    assert (
        m_out_q.return_value.put.call_args
        == [(msg, ), {}])


async def test_stdinstdoutprocessor_start(patches):
    processor = pipe.AStdinStdoutProcessor("PROTOCOL")
    patched = patches(
        "asyncio",
        ("AStdinStdoutProcessor.listener",
         dict(new_callable=PropertyMock)),
        ("AStdinStdoutProcessor.sender",
         dict(new_callable=PropertyMock)),
        ("AStdinStdoutProcessor.processor",
         dict(new_callable=PropertyMock)),
        "AStdinStdoutProcessor.log",
        prefix="aio.core.pipe.abstract.pipe")

    with patched as (m_asyncio, m_listen, m_send, m_proc, m_log):
        m_asyncio.gather.side_effect = AsyncMock()
        assert not await processor.start()

    assert (
        m_log.call_args_list
        == [[("PROCESSOR START", ), {}],
            [("PROCESSOR SHUTDOWN", ), {}]])
    assert (
        m_asyncio.gather.call_args
        == [(m_asyncio.create_task.return_value,
             m_asyncio.create_task.return_value,
             m_asyncio.create_task.return_value), {}])
    assert (
        m_asyncio.create_task.call_args_list
        == [[(m_listen.return_value, ), {}],
            [(m_send.return_value, ), {}],
            [(m_proc.return_value, ), {}]])
