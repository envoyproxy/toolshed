
import os
import pathlib
from functools import cached_property

import abstracts

from . import utils


class IDirectoryContext(metaclass=abstracts.Interface):
    """Directory context has `path` and an `in_directory` contextmanager."""

    @property  # type:ignore
    @abstracts.interfacemethod
    def path(self) -> pathlib.Path:
        raise NotImplementedError

    @property  # type:ignore
    @abstracts.interfacemethod
    def in_directory(self):
        """Context manager that `chdir`s to `self.path`."""
        raise NotImplementedError


@abstracts.implementer(IDirectoryContext)
class ADirectoryContext(metaclass=abstracts.Abstraction):
    _path: str | os.PathLike | None = None

    def __init__(
            self,
            path: str | os.PathLike) -> None:
        self._path = path

    @cached_property
    def path(self) -> pathlib.Path:
        return pathlib.Path(self._path or ".")

    @property
    def in_directory(self):
        return utils.directory_context(self.path)
