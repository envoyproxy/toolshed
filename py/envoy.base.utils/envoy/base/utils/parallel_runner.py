
import asyncio
import argparse
import os
import shlex
from collections.abc import Iterable, Iterator
from functools import cached_property
from itertools import batched

from aio.run import runner


class ParallelRunner(runner.Runner):

    @cached_property
    def batch_size(self) -> int:
        # Distribute items across cpu_count workers, rounded up via -(-x // y).
        return -(-len(self.items) // self.cpu_count) or 1

    @property
    def batches(self) -> Iterator[tuple[str, ...]]:
        yield from batched(self.items, self.batch_size)

    @cached_property
    def cpu_count(self) -> int:
        return os.cpu_count() or 1

    @property
    def items(self) -> list[str]:
        return self.args.items

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("command", type=str)
        parser.add_argument("items", nargs="+")
        super().add_arguments(parser)

    def command(self, batch: Iterable[str]) -> tuple[str, ...]:
        return tuple([*shlex.split(self.args.command), *batch])

    def handle_result(self, command: str, lines: Iterable[str]) -> None:
        result = "\n > ".join(lines)
        result = f"\n > {result}" if result else ""
        self.log.success(f"{command}{result}")

    async def run(self) -> None:
        results = await asyncio.gather(
            *[self._run(self.command(batch))
              for batch
              in self.batches])
        for argv, lines in results:
            self.handle_result(shlex.join(argv), lines)

    async def _run(
            self,
            argv: tuple[str, ...]) -> tuple[tuple[str, ...], list[str]]:
        proc = await asyncio.create_subprocess_exec(
            *argv,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE)
        stdout, stderr = await proc.communicate()
        if stderr:
            self.log.warning(f'({shlex.join(argv)})\n{stderr.decode()}')
        return argv, [line for line in stdout.decode().split("\n") if line]
