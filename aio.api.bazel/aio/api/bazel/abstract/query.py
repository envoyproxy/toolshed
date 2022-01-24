
import subprocess
from typing import Dict, List, Tuple

import abstracts

from aio.api.bazel import exceptions
from .base import ABazelCommand


class ABazelQuery(ABazelCommand, metaclass=abstracts.Abstraction):
    """Execute a bazel query asynchronously."""

    async def __call__(self, *args, **kwargs) -> List[str]:
        return await self.query(*args, **kwargs)

    @property
    def query_kwargs(self) -> Dict[str, str]:
        """Subprocess kwargs for running the Bazel query."""
        return dict(
            cwd=str(self.path),
            encoding="utf-8")

    async def query(
            self,
            expression: str,
            **kwargs) -> List[str]:
        """Run the Bazel query and return a response if no errors."""
        return self.handle_query_response(
            await self.run_query(expression, **kwargs))

    def handle_query_response(
            self,
            response: subprocess.CompletedProcess) -> List[str]:
        """Handle the subprocess response from running the query."""
        if self.query_failed(response):
            raise exceptions.BazelQueryError(
                f"\n{response.stdout.strip()}{response.stderr.strip()}")
        return response.stdout.strip().split("\n")

    def query_command(self, expression: str) -> Tuple[str, str, str]:
        """The Bazel query command."""
        return str(self.bazel_path), "query", expression

    def query_failed(self, response: subprocess.CompletedProcess) -> bool:
        """Check if the query response implies failure."""
        return bool(
            response.returncode
            or response.stdout.strip().startswith("[bazel release"))

    async def run_query(
            self,
            expression: str,
            **kwargs) -> subprocess.CompletedProcess:
        """Run the Bazel query in a subprocess."""
        query_kwargs = self.query_kwargs.copy()
        query_kwargs.update(kwargs)
        return await self.subproc_run(
            self.query_command(expression),
            **query_kwargs)
