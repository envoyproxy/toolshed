
import os
import pathlib
from contextlib import contextmanager


@contextmanager
def directory_context(path: str | pathlib.Path):
    """Sets the directory context."""
    origin = pathlib.Path().absolute()
    try:
        os.chdir(path)
        yield
    finally:
        os.chdir(origin)
