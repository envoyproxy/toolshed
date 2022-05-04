#
# Provides shared utils used by other python modules
#

import contextlib
import datetime
import os
import pathlib
import tarfile
import tempfile
from configparser import ConfigParser
from typing import (
    Any, AsyncGenerator, Callable, Generator,
    Iterator, List, Optional, Set, Type, Union)

from packaging import version

import pytz

import yaml

from trycast import trycast  # type:ignore

from .exceptions import TypeCastingError

from aio.core import functional


# See here for a list of known tar file extensions:
#   https://en.wikipedia.org/wiki/Tar_(computing)#Suffixes_for_compressed_files
# not all are listed here, and some extensions may require additional software
# to handle. This list can be updated as required
TAR_EXTS: Set[str] = {"tar", "tar.gz", "tar.xz", "tar.bz2"}


class ExtractError(Exception):
    pass


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


def extract(
        path: Union[pathlib.Path, str],
        *tarballs: Union[pathlib.Path, str]) -> pathlib.Path:
    if not tarballs:
        raise ExtractError(f"No tarballs specified for extraction to {path}")
    openers = functional.nested(
        *tuple(tarfile.open(tarball) for tarball in tarballs))

    with openers as tarfiles:
        for tar in tarfiles:
            tar.extractall(path=path)
    return pathlib.Path(path)


@contextlib.contextmanager
def untar(*tarballs: Union[pathlib.Path, str]) -> Iterator[pathlib.Path]:
    """Untar a tarball into a temporary directory.

    for example to list the contents of a tarball:

    ```
    import os

    from tooling.base.utils import untar


    with untar("path/to.tar") as tmpdir:
        print(os.listdir(tmpdir))

    ```

    the created temp directory will be cleaned up on
    exiting the contextmanager
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        yield extract(tmpdir, *tarballs)


def from_yaml(path: Union[pathlib.Path, str], type: Type = None) -> Any:
    """Returns the loaded python object from a yaml file given by `path`"""
    data = yaml.safe_load(pathlib.Path(path).read_text())
    return (
        data
        if type is None
        else typed(type, data))


def to_yaml(
        data: Union[dict, list, str, int],
        path: Union[pathlib.Path, str]) -> pathlib.Path:
    """For given `data` dumps as yaml to provided `path`.

    Returns `path`
    """
    path = pathlib.Path(path)
    path.write_text(yaml.dump(data))
    return path


def is_tarlike(path: Union[pathlib.Path, str]) -> bool:
    """Returns a bool based on whether a file looks like a tar file depending
    on its file extension.

    This allows for a provided path to save to, to dynamically be either
    considered a directory (to create) or a tar file (to create).
    """
    return any(str(path).endswith(ext) for ext in TAR_EXTS)


def ellipsize(text: str, max_len: int) -> str:
    """Truncate strings to a given length with an ellipsis suffix where
    required."""
    if len(text) <= max_len:
        return text
    return f"{text[:max_len - 3]}..."


def typed(tocast: Type, value: Any) -> Any:
    """Attempts to cast a value to a given type, TypeVar, or TypeDict.

    raises TypeError if cast value is `None`
    """

    if trycast(tocast, value) is not None:
        return value
    raise TypeCastingError(
        "Value has wrong type or shape for Type "
        f"{tocast}: {ellipsize(str(value), 10)}")


async def async_list(
        gen: AsyncGenerator,
        filter: Optional[Callable] = None) -> List:
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
        path: Union[pathlib.Path, str]) -> Generator[None, None, None]:
    """Changes working directory to given path and returns to previous working
    directory on exit."""
    prev_cwd = pathlib.Path.cwd()
    try:
        os.chdir(path)
        yield
    finally:
        os.chdir(prev_cwd)


def to_bytes(data: Union[str, bytes]) -> bytes:
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


def tar_mode(path: Union[pathlib.Path, str], mode="r") -> str:
    suffixes = ["gz", "bz2", "xz"]
    for suffix in suffixes:
        if str(path).endswith(f".{suffix}"):
            return f"{mode}:{suffix}"
    return mode


def dt_to_utc_isoformat(dt: datetime.datetime) -> str:
    """Convert a `datetime` -> UTC `date.isoformat`"""
    date = dt.replace(tzinfo=pytz.UTC)
    return date.date().isoformat()


def last_n_bytes_of(target: Union[str, pathlib.Path], n: int = 1) -> bytes:
    """Return the last `n` bytes from a file, defaults to 1 byte."""
    with open(target, "rb") as f:
        f.seek(0, os.SEEK_END)
        f.seek(f.tell() - n)
        return f.read(n)


def minor_version_for(_version: version.Version) -> version.Version:
    return version.Version(f"{_version.major}.{_version.minor}")
