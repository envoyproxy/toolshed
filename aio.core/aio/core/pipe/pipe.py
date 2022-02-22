
import abstracts

from aio.core import pipe


@abstracts.implementer(pipe.AStdinStdoutProcessor)
class StdinStdoutProcessor:
    pass
