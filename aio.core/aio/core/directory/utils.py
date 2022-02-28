
import os
import pathlib
from contextlib import contextmanager
from typing import Union


@contextmanager
def directory_context(path: Union[str, pathlib.Path]):
    """Sets the directory context."""
    origin = pathlib.Path().absolute()
    try:
        os.chdir(path)
        yield
    finally:
        os.chdir(origin)
