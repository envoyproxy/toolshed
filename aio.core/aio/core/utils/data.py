
import json
import pathlib
import tarfile
from typing import Any, Optional, Type, Union

import yaml

from aio.core import functional, utils


# See here for a list of known tar file extensions:
#   https://en.wikipedia.org/wiki/Tar_(computing)#Suffixes_for_compressed_files
# not all are listed here, and some extensions may require additional software
# to handle. This list can be updated as required
TAR_EXTS: set[str] = {"tar", "tar.gz", "tar.xz", "tar.bz2"}


def ellipsize(text: str, max_len: int) -> str:
    """Truncate strings to a given length with an ellipsis suffix where
    required."""
    if len(text) <= max_len:
        return text
    return f"{text[:max_len - 3]}..."


def extract(
        path: Union[pathlib.Path, str],
        *tarballs: Union[pathlib.Path, str]) -> pathlib.Path:
    if not tarballs:
        raise utils.ExtractError(
            f"No tarballs specified for extraction to {path}")
    openers = functional.nested(
        *tuple(tarfile.open(tarball) for tarball in tarballs))

    with openers as tarfiles:
        for tar in tarfiles:
            tar.extractall(path=path)
    return pathlib.Path(path)


def from_json(
        path: Union[pathlib.Path, str],
        type: Optional[Type] = None) -> Any:
    """Returns the loaded python object from a JSON file given by `path`"""
    data = json.loads(pathlib.Path(path).read_text())
    return (
        data
        if type is None
        else functional.utils.typed(type, data))


def from_yaml(
        path: Union[pathlib.Path, str],
        type: Optional[Type] = None) -> Any:
    """Returns the loaded python object from a yaml file given by `path`"""
    data = yaml.safe_load(pathlib.Path(path).read_text())
    return (
        data
        if type is None
        else functional.utils.typed(type, data))


def is_sha(text: str) -> bool:
    if len(text) != 40:
        return False
    try:
        int(text, 16)
    except ValueError:
        return False
    return True


def is_tarlike(path: Union[pathlib.Path, str]) -> bool:
    """Returns a bool based on whether a file looks like a tar file depending
    on its file extension.

    This allows for a provided path to save to, to dynamically be either
    considered a directory (to create) or a tar file (to create).
    """
    return any(str(path).endswith(ext) for ext in TAR_EXTS)


def to_yaml(
        data: Union[dict, list, str, int],
        path: Union[pathlib.Path, str]) -> pathlib.Path:
    """For given `data` dumps as yaml to provided `path`.

    Returns `path`
    """
    path = pathlib.Path(path)
    path.write_text(yaml.dump(data))
    return path
