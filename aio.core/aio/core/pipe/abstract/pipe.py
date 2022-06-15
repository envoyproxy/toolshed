
import argparse
import asyncio
import sys
from functools import cached_property
from typing import Any, Awaitable, Callable, TextIO, Tuple

import abstracts

from aio.core.functional import async_property
from aio.core.pipe import interface


@abstracts.implementer(interface.IProcessProtocol)
class AProcessProtocol(metaclass=abstracts.Abstraction):

    @classmethod
    def add_protocol_arguments(cls, parser: argparse.ArgumentParser) -> None:
        pass

    def __init__(
            self,
            processor: interface.IProcessor,
            args: argparse.Namespace) -> None:
        self.processor = processor
        self.args = args

    async def __call__(self, request: Any) -> Any:
        return await self.process(request)

    @abstracts.interfacemethod
    async def process(self, request: Any) -> Any:
        raise NotImplementedError


@abstracts.implementer(interface.IStdinStdoutProcessor)
class AStdinStdoutProcessor(metaclass=abstracts.Abstraction):

    def __init__(
            self,
            protocol: Callable[
                [interface.IStdinStdoutProcessor],
                Awaitable[interface.IProcessProtocol]],
            stdin: TextIO = sys.stdin,
            stdout: TextIO = sys.stdout,
            log: Callable[[str], None] = None) -> None:
        self._protocol = protocol
        self.stdin = stdin
        self.stdout = stdout
        self._log = log

    async def __call__(self) -> None:
        await self.start()

    @cached_property
    def connecting(self) -> asyncio.Lock:
        return asyncio.Lock()

    @async_property(cache=True)
    async def connection(
            self) -> Tuple[
                asyncio.StreamReader,
                asyncio.StreamWriter]:
        await self.loop.connect_read_pipe(
            lambda: self.stream_protocol,
            self.stdin)
        return self.stream_reader, await self.stream_writer

    @cached_property
    def in_q(self) -> asyncio.Queue:
        return asyncio.Queue()

    @async_property
    async def listener(self) -> None:
        async with self.connecting:
            reader = await self.reader
        self.log(f"START LISTENING {reader}")
        while True:
            line = await reader.readline()
            if not line:
                break
            if not line.strip():
                continue
            await self.in_q.put(line.decode())
        self.log("STOP LISTENING")
        await self.in_q.put("")

    @cached_property
    def loop(self) -> asyncio.AbstractEventLoop:
        return asyncio.get_event_loop()

    @cached_property
    def out_q(self) -> asyncio.Queue:
        return asyncio.Queue()

    @async_property
    async def processor(self) -> None:
        async with self.connecting:
            protocol = await self.protocol
        self.log(f"START PROCESSING {protocol}")
        while True:
            recv = await self.recv()
            if not recv:
                break
            await self.send(await self.process(recv))
            self.complete()
        self.log("STOP PROCESSING")
        await self.send("")

    @async_property(cache=True)
    async def protocol(self) -> interface.IProcessProtocol:
        return await self._protocol(self)

    @async_property
    async def reader(self) -> asyncio.StreamReader:
        return (await self.connection)[0]

    @async_property
    async def sender(self) -> None:
        async with self.connecting:
            writer = await self.writer
        self.log(f"START SENDING {writer}")
        while True:
            outgoing = await self.out_q.get()
            if not outgoing:
                break
            self.out_q.task_done()
            writer.write(outgoing.encode())
        self.log("STOP SENDING")

    @cached_property
    def stream_protocol(self) -> asyncio.StreamReaderProtocol:
        return asyncio.StreamReaderProtocol(self.stream_reader)

    @cached_property
    def stream_reader(self) -> asyncio.StreamReader:
        return asyncio.StreamReader()

    @async_property(cache=True)
    async def stream_transport(
            self) -> Tuple[
                asyncio.WriteTransport,
                asyncio.streams.FlowControlMixin]:
        return await self.loop.connect_write_pipe(
            asyncio.streams.FlowControlMixin,
            self.stdout)

    @async_property(cache=True)
    async def stream_writer(self) -> asyncio.StreamWriter:
        transport, flow = await self.stream_transport
        return asyncio.StreamWriter(
            transport,
            flow,
            self.stream_reader,
            self.loop)

    @async_property
    async def writer(self) -> asyncio.StreamWriter:
        return (await self.connection)[1]

    def complete(self) -> None:
        self.in_q.task_done()

    def log(self, message: str) -> None:
        if self._log:
            self._log(f"{message}\n")

    async def process(self, data: Any) -> Any:
        protocol = await self.protocol
        self.log(f"PROCESS: {protocol} {data}")
        return await protocol(data)

    async def recv(self) -> Any:
        recv = await self.in_q.get()
        self.log(f"RECV: {recv}")
        return recv

    async def send(self, msg: Any) -> None:
        self.log(f"SEND: {msg}")
        await self.out_q.put(msg)

    async def start(self) -> None:
        self.log("PROCESSOR START")
        await asyncio.gather(
            asyncio.create_task(self.listener),
            asyncio.create_task(self.sender),
            asyncio.create_task(self.processor))
        self.log("PROCESSOR SHUTDOWN")
