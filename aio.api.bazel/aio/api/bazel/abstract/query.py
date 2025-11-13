
import subprocess

import abstracts

from aio.api.bazel import exceptions
from .base import ABazelCommand


class ABazelQuery(ABazelCommand, metaclass=abstracts.Abstraction):
    """Execute a bazel query asynchronously."""

    async def __call__(self, *args, **kwargs) -> list[str]:
        return await self.query(*args, **kwargs)

    @property
    def query_kwargs(self) -> dict[str, str]:
        """Subprocess kwargs for running the Bazel query."""
        return dict(
            cwd=str(self.path),
            encoding="utf-8")

    async def query(
            self,
            expression: str,
            query_options: tuple[str, ...] | None = None,
            **kwargs) -> list[str]:
        """Run the Bazel query and return a response if no errors."""
        return self.handle_query_response(
            await self.run_query(
                expression,
                query_options=query_options,
                **kwargs))

    def handle_query_response(
            self,
            response: subprocess.CompletedProcess) -> list[str]:
        """Handle the subprocess response from running the query."""
        if self.query_failed(response):
            raise exceptions.BazelQueryError(
                f"\n{response.stdout.strip()}{response.stderr.strip()}")
        return response.stdout.strip().split("\n")

    def query_command(
            self,
            expression: str,
            query_options: tuple[str, ...] | None = None) -> tuple[str, ...]:
        """The Bazel query command."""
        return (
            str(self.bazel_path),
            *self.bazel_startup_options,
            "query",
            *(query_options or []),
            expression)

    def query_failed(self, response: subprocess.CompletedProcess) -> bool:
        """Check if the query response implies failure."""
        return bool(
            response.returncode
            or response.stdout.strip().startswith("[bazel release"))

    async def run_query(
            self,
            expression: str,
            query_options: tuple[str, ...] | None = None,
            **kwargs) -> subprocess.CompletedProcess:
        """Run the Bazel query in a subprocess."""
        query_kwargs = self.query_kwargs.copy()
        query_kwargs.update(kwargs)
        cmd = self.query_command(expression, query_options)
        return await self.subproc_run(
            cmd,
            **query_kwargs)
