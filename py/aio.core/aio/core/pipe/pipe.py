
import abstracts

from aio.core import pipe


@abstracts.implementer(pipe.IStdinStdoutProcessor)
class StdinStdoutProcessor(pipe.AStdinStdoutProcessor):
    pass
