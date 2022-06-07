
import asyncio
import argparse
import math
import os
from functools import cached_property
from typing import Iterable, Iterator, List, Tuple

from aio.run import runner


class ParallelRunner(runner.Runner):

    @cached_property
    def batch_size(self) -> int:
        return math.ceil(len(self.items) / self.cpu_count)

    @property
    def batches(self) -> Iterator[Iterable[str]]:
        for i in range(0, self.cpu_count):
            start, stop = (
                i * self.batch_size,
                (i + 1) * self.batch_size)
            if items := self.items[start: stop]:
                yield items

    @cached_property
    def cpu_count(self) -> int:
        return os.cpu_count() or 1

    @property
    def items(self) -> List[str]:
        return self.args.items

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("command", type=str)
        parser.add_argument("items", nargs="+")
        super().add_arguments(parser)

    def command(self, batch: Iterable[str]) -> str:
        return " ".join([*self.args.command.split(" "), *batch])

    def handle_result(self, cmd: str, lines: Iterable[str]) -> None:
        result = "\n > ".join(lines)
        result = f"\n > {result}" if result else ""
        self.log.success(f"{cmd}{result}")

    async def run(self) -> None:
        results = await asyncio.gather(
            *[self._run(self.command(batch))
              for batch
              in self.batches])
        for cmd, lines in results:
            self.handle_result(cmd, lines)

    async def _run(self, cmd: str) -> Tuple[str, List[str]]:
        proc = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE)
        stdout, stderr = await proc.communicate()
        if stderr:
            self.log.warning(f'({cmd})\n{stderr.decode()}')
        return cmd, [line for line in stdout.decode().split("\n") if line]
