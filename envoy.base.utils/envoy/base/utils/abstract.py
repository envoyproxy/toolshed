#!/usr/bin/env python3

import abc
import pathlib
import subprocess
from typing import List, Mapping, Tuple

import abstracts


class BazelQueryError(Exception):
    pass


class ABazelQuery(metaclass=abstracts.Abstraction):
    """Execute a bazel query.

    This allows running queries that do not define scope and cannot be run as
    genqueries.
    """

    @property
    @abc.abstractmethod
    def path(self) -> pathlib.Path:
        """Path to the Bazel workspace"""
        raise NotImplementedError

    @property
    def query_kwargs(self) -> Mapping:
        """Subprocess kwargs for running the Bazel query"""
        return dict(
            cwd=str(self.path),
            encoding="utf-8",
            capture_output=True)

    def query(self, expression: str) -> List[str]:
        """Run the Bazel query and return a response if no errors"""
        return self.handle_query_response(self.run_query(expression))

    def handle_query_response(
            self,
            response: subprocess.CompletedProcess) -> List[str]:
        """Handle the subprocess response from running the query"""
        if self.query_failed(response):
            raise BazelQueryError(
                f"\n{response.stdout.strip()}{response.stderr.strip()}")
        return response.stdout.strip().split("\n")

    def query_command(self, expression: str) -> Tuple[str, ...]:
        """The Bazel query command"""
        return "bazel", "query", expression

    def query_failed(self, response: subprocess.CompletedProcess) -> bool:
        """Check if the query response implies failure"""
        return bool(
            response.returncode
            or response.stdout.strip().startswith("[bazel release"))

    def run_query(self, expression: str) -> subprocess.CompletedProcess:
        """Run the Bazel query in a subprocess"""
        return subprocess.run(
            self.query_command(expression),
            **self.query_kwargs)
