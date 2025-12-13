
import abc
import logging
import os
import subprocess
from functools import cached_property
from typing import Any, Mapping, Sequence

import abstracts

from aio.core import directory
from aio.core.dev import debug


class ISubprocessHandler(
        directory.IDirectoryContext,
        metaclass=abstracts.Interface):
    """Protocol for handling subprocess calls."""

    @property  # type:ignore
    @abstracts.interfacemethod
    def args(self) -> Sequence[str]:
        raise NotImplementedError

    @property  # type:ignore
    @abstracts.interfacemethod
    def encoding(self) -> str:
        raise NotImplementedError

    @property  # type:ignore
    @abstracts.interfacemethod
    def kwargs(self) -> Mapping:
        raise NotImplementedError

    @abstracts.interfacemethod
    def handle(self, response: subprocess.CompletedProcess) -> Any:
        """Handle a successful response."""
        raise NotImplementedError

    @abstracts.interfacemethod
    def handle_error(self, response: subprocess.CompletedProcess) -> Any:
        """Handle a failing response."""
        raise NotImplementedError

    @abstracts.interfacemethod
    def handle_response(self, response: subprocess.CompletedProcess) -> Any:
        """Handle a response."""
        raise NotImplementedError

    @abstracts.interfacemethod
    def has_failed(self, response: subprocess.CompletedProcess) -> bool:
        raise NotImplementedError

    @abstracts.interfacemethod
    def run(self,
            *args: str,
            **kwargs) -> Any:
        """Run the subprocess, returning handled results."""
        raise NotImplementedError

    @abstracts.interfacemethod
    def run_subprocess(
            self,
            *args: str,
            **kwargs) -> subprocess.CompletedProcess:
        """Run the subprocess."""
        raise NotImplementedError

    @abstracts.interfacemethod
    def subprocess_args(self, *args: str) -> tuple[Sequence[str], ...]:
        """Derive the subprocess args, from init args and supplied args."""
        raise NotImplementedError

    @abstracts.interfacemethod
    def subprocess_kwargs(self, **kwargs):
        """Derive the subprocess kwargs, from init kwargs and supplied
        kwargs."""
        raise NotImplementedError


@abstracts.implementer(ISubprocessHandler)
class ASubprocessHandler(
        directory.ADirectoryContext,
        metaclass=abstracts.Abstraction):
    _args: Sequence[str]
    _kwargs: Mapping
    _encoding: str

    def __init__(
            self,
            path: str | os.PathLike,
            *args: str,
            encoding: str = "utf-8",
            **kwargs) -> None:
        directory.ADirectoryContext.__init__(self, path)
        self._encoding = encoding
        self._args = args
        self._kwargs = kwargs

    def __call__(self, *args: str) -> Any:
        return self.run(*args)

    def __str__(self) -> str:
        return f"{self.__class__.__module__}.{self.__class__.__name__}"

    @property
    def args(self) -> Sequence[str]:
        return (
            self._args
            if self._args
            else ())

    @property
    def encoding(self) -> str:
        return self._encoding

    @property
    def kwargs(self) -> Mapping:
        return dict(
            cwd=self.path,
            capture_output=True,
            encoding=self.encoding)

    @cached_property
    def log(self) -> logging.Logger:
        """Logger to use - derived from implementer name."""
        return logging.getLogger(str(self))

    @abc.abstractmethod
    def handle(
            self,
            response: subprocess.CompletedProcess) -> Any:
        return dict(
            RESPONSE=[
                response.returncode,
                response.stdout,
                response.stderr])

    @abc.abstractmethod
    def handle_error(
            self,
            response: subprocess.CompletedProcess) -> Any:
        return dict(
            ERROR=[
                response.returncode,
                response.stdout,
                response.stderr])

    def handle_response(
            self,
            response: subprocess.CompletedProcess) -> Any:
        return (
            self.handle_error(response)
            if self.has_failed(response)
            else self.handle(response))

    def has_failed(self, response: subprocess.CompletedProcess) -> bool:
        return bool(response.returncode)

    @debug.logging(
        log="self.log",
        show_cpu=True)
    def run(self, *args, **kwargs) -> Any:
        """Run the subprocess and handle the results."""
        return self.handle_response(
            self.run_subprocess(
                *self.subprocess_args(*args, **kwargs),
                **self.subprocess_kwargs(*args, **kwargs)))

    def run_subprocess(
            self,
            *args,
            **kwargs) -> subprocess.CompletedProcess:
        return subprocess.run(*args, **kwargs)

    def subprocess_args(self, *args, **kwargs) -> tuple[Sequence[str], ...]:
        return ((*self.args, *args), )

    def subprocess_kwargs(self, *args, **kwargs) -> Mapping:
        return {**self.kwargs, **kwargs}
