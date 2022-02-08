
import asyncio
import abc
import shutil
from functools import cached_property
from typing import Any, Type

import abstracts

from aio.core.functional import async_property
from aio.core.tasks import concurrent
from aio.core.interactive import Interactive


class AspellPipe:
    handlers = []

    def __init__(self, in_q, out_q):
        self.in_q = in_q
        self.out_q = out_q

    @async_property(cache=True)
    async def proc(self):
        return await asyncio.create_subprocess_exec(
            "/home/phlax/.virtualenvs/envoydev/pytooling/echo.py",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE)

    async def listen(self):
        print ("STARTING LISTENER")
        while True:
            msg = await self.in_q.get()
            print(f"IN Q MESSAGE RECVD: {msg}")
            self.in_q.task_done()
            print(f"Sending message to process: {msg}")
            result = await self.write(msg)
            await self.out_q.put(result)

    async def start(self):
        print ("STARTING ASPELL")
        self.task = asyncio.create_task(self.listen())
        return (await self.write(b""))[0]

    async def stop(self):
        print ("STOPPING ASPELL")

    async def write(self, message):
        print(f"WRITE: {message}")
        proc = await self.proc
        stdout, stderr = await proc.communicate(message)
        other = await proc.stdout.read()
        more = await proc.communicate(message)
        return stdout, stderr


class MultiPipe:

    def __init__(self, pipe_type):
        self.pipe_type = pipe_type

    @cached_property
    def in_q(self):
        return asyncio.Queue()

    @cached_property
    def out_q(self):
        return asyncio.Queue()

    @async_property(cache=True)
    async def pipes(self):
        aspell_pipe = self.pipe_type(self.in_q, self.out_q)
        print(f"Started aspell pipe: {await aspell_pipe.start()}")
        return aspell_pipe

    async def write(self, message):
        print(f"PUTTING MESSAGE: {message}")
        print(f"IN Q: {self.in_q}")
        await self.in_q.put(message)
        print(f"DONE")
        while True:
            stdout, stderr = await self.out_q.get()
            self.out_q.task_done()
            if stdout or stderr:
                return stdout, stderr


class AAspellAPI(metaclass=abstracts.Abstraction):
    """Aspell API wrapper.
    """

    def __init__(self, *args, **kwargs) -> None:
        self.args = args
        self.kwargs = kwargs

    @cached_property
    def aspell_command(self):
        command = shutil.which("aspell")
        return f"{command} -a"

    @async_property(cache=True)
    async def session(self):
        session = Interactive(self.aspell_command, 1)
        await session.start()
        return session

    async def compile_dictionary(self, path):
        # breakpoint()
        pass

    @async_property(cache=True)
    async def pipe(self):
        aspell_pipe = MultiPipe(AspellPipe)
        await aspell_pipe.pipes
        # await aspell_pipe.start()
        return aspell_pipe

    async def listener(self):
        print(f"MESSAGE RCVD: {stdout} {stderr}")

    async def spellcheck(self, message):
        pipe = await self.pipe
        return await pipe.write(message)

    async def start(self):
        await self.session

    async def compile_dictionary(self, dictionary):
        words = ["asdfasfdafds", "cabbage"]
        session = await self.session
        for word in words:
            response = await session(f"{word}\n".encode("utf-8"))
            if str(response[0]).strip() == "*":
                print(f"{word} is a good word")
            else:
                print(f"{word} is a bad word")

    async def stop(self):
        pass
