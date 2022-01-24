
import subprocess

import abstracts

from aio.api.bazel import exceptions
from . import ABazelCommand


class ABazelRun(ABazelCommand, metaclass=abstracts.Abstraction):
    """Execute a bazel run asynchronously."""

    async def __call__(self, *args, **kwargs) -> subprocess.CompletedProcess:
        return await self.run(*args, **kwargs)

    async def run(
            self,
            target: str,
            *args,
            capture_output: bool = False,
            cwd: str = "",
            raises: bool = True) -> subprocess.CompletedProcess:
        """Run a bazel target and return the subprocess response."""
        args = (("--",) + args) if args else args
        bazel_args = (self.bazel_path, "run", target) + args
        resp = await self.subproc_run(
            bazel_args,
            capture_output=capture_output)
        if resp.returncode and raises:
            raise exceptions.BazelRunError(f"Bazel run failed: {resp}")
        return resp
