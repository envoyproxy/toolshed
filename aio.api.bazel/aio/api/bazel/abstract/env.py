
import subprocess
from functools import cached_property
from typing import List, Type

import abstracts

from aio.api.bazel import abstract

from .base import ABazel


class ABazelEnv(ABazel, metaclass=abstracts.Abstraction):
    """Bazel environment with async methods for querying, and running bazel."""

    @cached_property
    def bazel_query(self) -> "abstract.ABazelQuery":
        return self.bazel_query_class(self.path, bazel_path=self.bazel_path)

    @property  # type: ignore
    @abstracts.interfacemethod
    def bazel_query_class(self) -> Type["abstract.ABazelQuery"]:
        raise NotImplementedError

    @cached_property
    def bazel_run(self) -> "abstract.ABazelRun":
        return self.bazel_run_class(self.path, bazel_path=self.bazel_path)

    @property  # type: ignore
    @abstracts.interfacemethod
    def bazel_run_class(self) -> Type["abstract.ABazelRun"]:
        raise NotImplementedError

    async def query(self, query: str, **kwargs) -> List:
        """Run a bazel query and return stdout as list of lines."""
        return await self.bazel_query(query, **kwargs)

    async def run(
            self,
            command: str,
            *args,
            **kwargs) -> subprocess.CompletedProcess:
        """Run a bazel query and return stdout as list of lines."""
        return await self.bazel_run(command, *args, **kwargs)
