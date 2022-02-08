
import asyncio
import re
import sys
import time
from functools import cached_property, partial
from typing import Union

import abstracts

from aio.core import functional, output, subprocess
from aio.core.functional import async_property, AwaitableGenerator


class APrompt(metaclass=abstracts.Abstraction):

    def __init__(self, match, match_type="any"):
        self._match = match
        self.match_type = match

    @cached_property
    def re_match(self):
        return re.compile(self._match)

    def matches(self, counter, output):
        # print(counter)
        if isinstance(self._match, int):
            if counter.get("stdout", 0) >= self._match:
                return True
        return bool(self.re_match.match(str(output)))


class AInteractive(metaclass=abstracts.Abstraction):

    def __init__(self, cmd, prompt, flush_delay=0, wait_for_prompt=True, start_prompt=None):
        self.cmd = cmd
        self._prompt = prompt
        self._start_prompt = start_prompt or prompt
        self.flush_delay = flush_delay
        self.wait_for_prompt = wait_for_prompt

    @cached_property
    def buffer(self):
        return asyncio.Queue()

    @cached_property
    def prompt(self):
        return (
            self.prompt_class(self._prompt)
            if not isinstance(self._prompt, self.prompt_class)
            else prompt)

    @cached_property
    def start_prompt(self):
        return (
            self.prompt_class(self._start_prompt)
            if not isinstance(self._start_prompt, self.prompt_class)
            else start_prompt)

    @property
    def prompt_class(self):
        return Prompt

    @cached_property
    def write_lock(self):
        return asyncio.Lock()

    @cached_property
    def q(self):
        return asyncio.Queue()

    @async_property(cache=True)
    async def proc(self):
        return await asyncio.create_subprocess_shell(
            self.cmd,
            # shell=True,
            # universal_newlines=True,
            stdin=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE)

    async def connect_outputs(self):
        await self.stdout_listener
        await self.stderr_listener

    @async_property(cache=True)
    async def stderr_listener(self):
        return asyncio.create_task(
            self.listen_to_pipe(
                "stderr",
                (await self.proc).stderr))

    @async_property(cache=True)
    async def stdout_listener(self):
        return asyncio.create_task(
            self.listen_to_pipe(
                "stdout",
                (await self.proc).stdout))

    async def interact(self, message=None):
        await self.send_stdin(message)
        counter = dict()
        returns = False
        while True:
            result = await self.q.get()
            yield result
            counter[result.type] = counter.get(result.type, 0) + 1
            await self.buffer.get()
            self.buffer.task_done
            if self.interaction_returns(counter, result):
                returns = True
            if returns and await self.finished_reading:
                break

    @async_property
    async def finished_reading(self):
        if self.buffer.qsize():
            return False
        if not self.flush_delay:
            return True
        await asyncio.sleep(self.flush_delay)
        return not self.buffer.qsize()

    def interaction_returns(self, counter, result):
        return self.prompt.matches(counter, result)

    async def send_stdin(self, message):
        print(f"SEND STDIN {message}")
        async with self.write_lock:
            proc = await self.proc
            if message is not None:
                proc.stdin.write(message)
            await proc.stdin.drain()

    async def listen_to_pipe(self, type, pipe):
        while True:
            result = await pipe.readline()
            await self.buffer.put(None)
            # If we havent completed writing, wait
            async with self.write_lock:
                # print(f"GOT RESULT: {type}  {result}")
                await self.q.put(output.CapturedOutput(type, result))

    async def start(self):
        await self.connect_outputs()
        print("\n".join(str(h) for h in await self.header))
        self._started = True

    _started = False

    @cached_property
    def header(self):
        return (
            self(b"")
            if self.wait_for_prompt
            else None)

    def __call__(self, message=None):
        return AwaitableGenerator(self.interact(message))
