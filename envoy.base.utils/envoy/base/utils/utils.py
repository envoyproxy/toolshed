#
# Provides shared utils used by other python modules
#

import contextlib
import datetime
import os
import pathlib
import tempfile
from configparser import ConfigParser
from typing import (
    Any, AsyncGenerator, Callable, Generator,
    Iterator)

from packaging import version as _version

import pytz

import yaml

from trycast import isassignable  # type:ignore

from .exceptions import TypeCastingError

# condition needed due to https://github.com/bazelbuild/rules_python/issues/622
try:
    import orjson as json
except ImportError:
    import json  # type:ignore


# this is testing specific - consider moving to tools.testing.utils
@contextlib.contextmanager
def coverage_with_data_file(data_file: str) -> Iterator[str]:
    """This context manager takes the path of a data file and creates a custom
    coveragerc with the data file path included.

    The context is yielded the path to the custom rc file.
    """
    parser = ConfigParser()
    parser.read(".coveragerc")
    parser["run"]["data_file"] = data_file
    # use a temporary .coveragerc
    with tempfile.TemporaryDirectory() as tmpdir:
        tmprc = os.path.join(tmpdir, ".coveragerc")
        with open(tmprc, "w") as f:
            parser.write(f)
        yield tmprc


def from_json(
        path: pathlib.Path | str,
        type: type | None = None) -> Any:
    """Returns the loaded python object from a JSON file given by `path`"""
    data = json.loads(pathlib.Path(path).read_text())
    return (
        data
        if type is None
        else typed(type, data))


def from_yaml(
        path: pathlib.Path | str,
        type: type | None = None) -> Any:
    """Returns the loaded python object from a yaml file given by `path`"""
    data = yaml.safe_load(pathlib.Path(path).read_text())
    return (
        data
        if type is None
        else typed(type, data))


def to_yaml(
        data: dict | list | str | int,
        path: pathlib.Path | str) -> pathlib.Path:
    """For given `data` dumps as yaml to provided `path`.

    Returns `path`
    """
    path = pathlib.Path(path)
    path.write_text(yaml.dump(data))
    return path


def ellipsize(text: str, max_len: int) -> str:
    """Truncate strings to a given length with an ellipsis suffix where
    required."""
    if len(text) <= max_len:
        return text
    return f"{text[:max_len - 3]}..."


def typed(tocast: type, value: Any) -> Any:
    """Attempts to cast a value to a given type, TypeVar, or TypeDict.

    raises TypeError if cast value is `None`
    """
    if isassignable(value, tocast):
        return value
    raise TypeCastingError(
        "Value has wrong type or shape for "
        f"{tocast}\n{value}",
        value=value)


async def async_list(
        gen: AsyncGenerator,
        filter: Callable | None = None) -> list:
    """Turn an async generator into a here and now list, with optional
    filter."""
    results = []
    async for x in gen:
        if filter and not filter(x):
            continue
        results.append(x)
    return results


@contextlib.contextmanager
def cd_and_return(
        path: pathlib.Path | str) -> Generator[None, None, None]:
    """Changes working directory to given path and returns to previous working
    directory on exit."""
    prev_cwd = pathlib.Path.cwd()
    try:
        os.chdir(path)
        yield
    finally:
        os.chdir(prev_cwd)


def to_bytes(data: str | bytes) -> bytes:
    return (
        bytes(data, encoding="utf-8")
        if not isinstance(data, bytes)
        else data)


def is_sha(text: str) -> bool:
    if len(text) != 40:
        return False
    try:
        int(text, 16)
    except ValueError:
        return False
    return True


def dt_to_utc_isoformat(dt: datetime.datetime) -> str:
    """Convert a `datetime` -> UTC `date.isoformat`"""
    date = dt.replace(tzinfo=pytz.UTC)
    return date.date().isoformat()


def last_n_bytes_of(target: str | pathlib.Path, n: int = 1) -> bytes:
    """Return the last `n` bytes from a file, defaults to 1 byte."""
    with open(target, "rb") as f:
        f.seek(0, os.SEEK_END)
        f.seek(f.tell() - n)
        return f.read(n)


def minor_version_for(version: _version.Version) -> _version.Version:
    return _version.Version(f"{version.major}.{version.minor}")


def increment_version(
        version: _version.Version,
        patch: bool = False) -> _version.Version:
    return _version.Version(
        f"{version.major}.{version.minor}.{version.micro + 1}"
        if patch
        else f"{version.major}.{version.minor + 1}.{version.micro}")


class TuplePairError(Exception):
    pass


def tuple_pair(input: str, separator: str = ":") -> tuple[str, str]:
    """This allows dict generators to split items and pass type checking."""
    pair = input.split(separator)
    if len(pair) != 2:
        raise TuplePairError(
            f"Provided string did not split ({separator}) in 2: {input}")
    return pair[0], pair[1]
