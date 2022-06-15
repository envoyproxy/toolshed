
import argparse
import json
from functools import cached_property
from typing import Optional, Type

import abstracts

from aio.api.bazel import interface
from aio.core import pipe, utils
from aio.run import runner


@abstracts.implementer(interface.IBazelProcessProtocol)
class ABazelProcessProtocol(
        pipe.AProcessProtocol,
        metaclass=abstracts.Abstraction):

    @cached_property
    def parser(self) -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(fromfile_prefix_chars='@')
        self.add_arguments(parser)
        return parser

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("--in")
        parser.add_argument("--out")


@abstracts.implementer(interface.IBazelWorkerProcessor)
class ABazelWorkerProcessor(
        pipe.StdinStdoutProcessor,
        metaclass=abstracts.Abstraction):

    async def process(self, recv: argparse.Namespace) -> str:
        with utils.captured_warnings() as captured:
            captured.result = await super().process(recv)
        return str(captured)

    async def recv(self) -> argparse.Namespace:
        return await self._load(await super().recv())

    async def send(self, msg: Optional[str]) -> None:
        await super().send(self._dump(msg or ""))

    def _dump(self, msg: str) -> str:
        # TODO: add error handling
        return json.dumps(dict(exit_code=0, output=msg))

    async def _load(self, recv) -> argparse.Namespace:
        return (await self.protocol).parser.parse_args(
            json.loads(recv)["arguments"])


@abstracts.implementer(interface.IBazelWorker)
class ABazelWorker(runner.Runner, metaclass=abstracts.Abstraction):
    _use_uvloop = False

    @property
    def persistent(self) -> bool:
        return self.args.persistent_worker

    @property  # type:ignore
    @abstracts.interfacemethod
    def processor_class(self) -> Type[interface.IBazelWorkerProcessor]:
        raise NotImplementedError

    @cached_property
    def protocol_args(self) -> argparse.Namespace:
        parser = argparse.ArgumentParser()
        self.protocol_class.add_protocol_arguments(parser)
        return parser.parse_args(self.extra_args)

    @cached_property
    def protocol_class(self) -> Type[pipe.IProcessProtocol]:
        return utils.dottedname_resolve(self.args.protocol)

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("protocol")
        parser.add_argument("--persistent_worker", action="store_true")
        super().add_arguments(parser)

    async def protocol(
            self,
            processor: interface.IBazelWorkerProcessor) -> (
                interface.IBazelProcessProtocol):
        return self.protocol_class(processor, self.protocol_args)

    async def run(self) -> None:
        if self.persistent:
            await self.processor_class(self.protocol)()
        # TODO: implement one-shot op
