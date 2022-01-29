
import abstracts

from aio.core import subprocess


@abstracts.implementer(subprocess.AAsyncSubprocessRunner)
class AsyncSubprocessRunner:
    pass
