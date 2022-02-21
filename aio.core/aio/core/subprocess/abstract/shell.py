
import abc
import subprocess
import textwrap
from functools import cached_property
from typing import Any, Callable, Dict, List, Optional

import abstracts

from aio.core import event, functional
from aio.core.subprocess import (
    exceptions,
    parallel as _parallel,
    run as _run)


@abstracts.implementer(event.IExecutive)
class AAsyncShell(event.AExecutive, metaclass=abstracts.Abstraction):
    """Execute shell commands asynchronously.

    Wraps async `run` and `parallel` methods for an environment,
    with default kwargs.

    This class can be instantiated with kwargs and called with
    further kwargs which are merged to create kwargs for the subprocess
    runners - thus providing overrideable defaults.

    By default the shell will use a ProcessPoolExecutor - this can
    be overridden by setting `fork` to `False`.

    You can specify a handler for responses - the default is return
    a list split from `stdout`.

    This can be overridden by setting `handler`=`None`, to get `subprocess`
    responses, or to set a custom handler. The handler can also be
    overridden on calls to `run`.

    By default `run` will raise a `RunError` if it sees a `returncode` > 1.

    Setting raises, either when instantiating the class or in subsequent
    calls to `run` will prevent this.
    """

    def __init__(
            self,
            fork: bool = True,
            raises: bool = True,
            **kwargs) -> None:
        self._handler = kwargs.pop("handler", self.to_list)
        self._fork = fork
        self._raises = raises
        self._loop = kwargs.pop("loop", None)
        self._pool = kwargs.pop("pool", None)
        self._kwargs = kwargs

    async def __call__(self, *args, **kwargs) -> Any:
        return await self.run(*args, **kwargs)

    @property
    def default_kwargs(self) -> Dict:
        """Class default kwargs for calling subprocess utilities."""
        return dict(
            capture_output=True,
            encoding="utf-8")

    @property
    def fork(self) -> bool:
        """Flag to indicate whether to fork by default."""
        return self._fork

    @cached_property
    def handler(self) -> Optional[Callable]:
        """Default handler for subprocess responses."""
        return self._handler or (lambda x: x)

    @cached_property
    def kwargs(self) -> Dict:
        """Instantiated kwargs."""
        return {
            **self.default_kwargs,
            **self._kwargs}

    @property
    def raises(self) -> bool:
        """Flag indicating default behaviour on seeing a `returncode` > 0."""
        return self._raises

    @abc.abstractmethod
    def parallel(self, *args, **kwargs) -> "functional.AwaitableGenerator":
        """Wrapper around the `parallel` utility."""
        return _parallel(
            *args,
            **self.parallel_kwargs(**kwargs))

    def parallel_kwargs(self, **kwargs) -> Dict:
        """Construct kwargs for the `parallel` utility."""
        return {
            **dict(fork=self.fork),
            **self.kwargs,
            **kwargs}

    @abc.abstractmethod
    async def run(
            self,
            *args,
            **kwargs) -> Any:
        """Wrapper around the `run` utility."""
        run_kwargs = self.run_kwargs(**kwargs)
        return self._handle_response(
            run_kwargs.pop("handler"),
            run_kwargs.pop("raises"),
            await _run(*args, **run_kwargs))

    def run_kwargs(self, **kwargs) -> Dict:
        """Construct kwargs for the `run` utility."""
        kwargs = {**self.kwargs, **kwargs}
        return {
            **dict(
                handler=self.handler,
                raises=self.raises,
                executor=self.pool),
            **kwargs}

    def to_list(self, response: subprocess.CompletedProcess) -> List[str]:
        """Split the `stdout` from a `subprocess` response to a list."""
        return response.stdout.split("\n")

    def _handle_exception(self, response: subprocess.CompletedProcess) -> None:
        command = textwrap.shorten(
            " ".join(response.args),
            width=10,
            placeholder="...")
        output = "\n".join(
            out
            for out
            in [response.stdout, response.stderr]
            if out)
        output = f":\n{output}" if output else output
        raise exceptions.RunError(
            f"Run failed ({command}):{output}",
            response)

    def _handle_response(
            self,
            handler: Callable,
            raises: bool,
            response: subprocess.CompletedProcess) -> Any:
        if response.returncode and raises:
            return self._handle_exception(response)
        return handler(response)
