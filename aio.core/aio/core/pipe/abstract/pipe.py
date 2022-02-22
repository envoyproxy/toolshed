
import asyncio
import importlib
import sys
from functools import cached_property

import abstracts

from aio.core.functional import async_property


class AStdinStdoutProcessor(metaclass=abstracts.Abstraction):

    def __init__(self, stdin, stdout, processor, log=None):
        self.processor = processor
        self.stdin = stdin
        self.stdout = stdout
        self._log = log

    @cached_property
    def connecting(self):
        return asyncio.Lock()

    @async_property(cache=True)
    async def connection(self):
        reader = asyncio.StreamReader()
        protocol = asyncio.StreamReaderProtocol(reader)
        await self.loop.connect_read_pipe(lambda: protocol, self.stdin)
        w_transport, w_protocol = await self.loop.connect_write_pipe(asyncio.streams.FlowControlMixin, self.stdout)
        writer = asyncio.StreamWriter(w_transport, w_protocol, reader, self.loop)
        return reader, writer

    @async_property
    async def listener(self):
        async with self.connecting:
            reader = await self.reader
        self.log(f"LISTENING\n")
        while True:
            line = await reader.readline()
            if not line:
                self.log(f"CLOSED: {line}\n")
                break
            if not line.strip():
                continue
            # self.log(f"RCVD: {line}\n")
            await self.in_q.put(line)

    @async_property
    async def responder(self):
        async with self.connecting:
            writer = await self.writer
        self.log(f"RESPONDING\n")
        while True:
            outgoing = await self.out_q.get()
            self.out_q.task_done()
            # self.log(f"SEND: {outgoing}\n")
            writer.write(outgoing.encode("utf-8"))

    @async_property
    async def reader(self):
        return (await self.connection)[0]

    @async_property
    async def writer(self):
        return (await self.connection)[1]

    @cached_property
    def in_q(self):
        return asyncio.Queue()

    @cached_property
    def out_q(self):
        return asyncio.Queue()

    async def process(self, *args):
        await asyncio.gather(
            asyncio.create_task(self.processor(self.in_q, self.out_q, *args, log=self.log)),
            asyncio.create_task(self.listener),
            asyncio.create_task(self.responder))

    @cached_property
    def loop(self):
        return asyncio.get_event_loop()

    def __call__(self, *args):
        return self.process(*args)

    def log(self, message):
        if self._log:
            self._log(message)
