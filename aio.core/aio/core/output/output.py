
from typing import Type

import janus

import abstracts

from aio.core import output


@abstracts.implementer(output.ABufferedOutputs)
class BufferedOutputs:

    @property
    def io_class(self) -> Type[output.AQueueIO]:
        return self._io_class or QueueIO

    @property
    def output_class(self) -> Type[output.ACapturedOutput]:
        return self._output_class or CapturedOutput

    @property
    def queue_class(self) -> Type[janus.Queue]:
        return super().queue_class


@abstracts.implementer(output.ACapturedOutput)
class CapturedOutput:
    pass


@abstracts.implementer(output.ACapturedOutputs)
class CapturedOutputs:
    pass


@abstracts.implementer(output.AQueueIO)
class QueueIO:
    pass
