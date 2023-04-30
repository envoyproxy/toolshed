#
# Provides tar utils:
#   multi-path extraction, zst support, filtering
#

# TODO:
# - improve the inconsistent api here
# - use asyncio and move to aio.core
# - remove zst when https://bugs.python.org/issue37095 is resolved

import contextlib
import io
import pathlib
import shutil
import tarfile
import tempfile
from typing import (
    ContextManager, Iterator, Optional, Pattern, Set)

import zstandard

from aio.core import functional


# See here for a list of known tar file extensions:
#   https://en.wikipedia.org/wiki/Tar_(computing)#Suffixes_for_compressed_files
# not all are listed here, and some extensions may require additional software
# to handle. This list can be updated as required
TAR_EXTS: Set[str] = {"tar", "tar.gz", "tar.xz", "tar.bz2", "tar.zst"}
COMPRESSION_EXTS: Set[str] = {"gz", "bz2", "xz"}


class ExtractError(Exception):
    pass


def is_tarlike(path: pathlib.Path | str) -> bool:
    """Returns a bool based on whether a file looks like a tar file depending
    on its file extension.

    This allows for a provided path to save to, to dynamically be either
    considered a directory (to create) or a tar file (to create).
    """
    return any(str(path).endswith(ext) for ext in TAR_EXTS)


def tar_mode(path: pathlib.Path | str, mode="r") -> str:
    for suffix in COMPRESSION_EXTS:
        if str(path).endswith(f".{suffix}"):
            return f"{mode}:{suffix}"
    return mode


# Extraction

def extract(
        path: pathlib.Path | str,
        *tarballs: pathlib.Path | str,
        matching: Optional[Pattern[str]] = None,
        mappings: Optional[dict[str, str]] = None) -> pathlib.Path:
    if not tarballs:
        raise ExtractError(f"No tarballs specified for extraction to {path}")
    openers = functional.nested(
        *tuple(_open(tarball) for tarball in tarballs))
    path = pathlib.Path(path)

    with openers as tarfiles:
        for prefix, tar in tarfiles:
            _extract(path, prefix, tar, matching, mappings)

    _mv_paths(path, mappings)
    _rm_paths(path, matching)
    return path


@contextlib.contextmanager
def untar(
        *tarballs: pathlib.Path | str,
        matching: Optional[Pattern[str]] = None,
        mappings: Optional[dict[str, str]] = None) -> Iterator[pathlib.Path]:
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
        yield extract(
            tmpdir, *tarballs,
            matching=matching,
            mappings=mappings)


def _extract(
        path: pathlib.Path,
        prefix: str,
        tar: tarfile.TarFile,
        matching: Optional[Pattern[str]],
        mappings: Optional[dict[str, str]]) -> None:
    if not matching:
        tar.extractall(path=path.joinpath(prefix))
        return
    for member in tar.getmembers():
        if _should_extract(member, matching, mappings):
            tar.extract(
                member,
                path=path.joinpath(prefix).joinpath(member.name))


def _mv_paths(path: pathlib.Path, mappings: Optional[dict[str, str]]) -> None:
    for src, dest in (mappings or {}).items():
        src_path = path.joinpath(src)
        dest_path = path.joinpath(dest)
        dest_path.parent.mkdir(exist_ok=True, parents=True)
        shutil.move(src_path, dest_path)


def _open(
        path: pathlib.Path | str) -> (
            ContextManager[tuple[str, tarfile.TarFile]]):
    """For a given tarball path if it contains `:` split prefix, path,
    otherwise prefix is empty.

    If the tarfile is `tar.zst` use zstd to decompress.

    Return prefix, and opened tarfile for path.
    """
    _path = str(path)
    prefix, _path = (
        _path.split(":")
        if ":" in _path
        else ("", _path))
    return (
        _opener(_open_zst(_path), prefix)
        if _path.endswith(".zst")
        else _opener(tarfile.open(_path), prefix))


def _open_zst(path: pathlib.Path | str) -> tarfile.TarFile:
    """extract .zst file."""
    archive = pathlib.Path(path).expanduser()
    dctx = zstandard.ZstdDecompressor()
    outfile = io.BytesIO()
    with archive.open("rb") as infile:
        dctx.copy_stream(infile, outfile)
    outfile.seek(0)
    return tarfile.open(fileobj=outfile)


@contextlib.contextmanager
def _opener(
        tarball: tarfile.TarFile,
        prefix: str = "") -> Iterator[tuple[str, tarfile.TarFile]]:
    with tarball as t:
        yield prefix, t


def _rm_paths(path: pathlib.Path, matching: Optional[Pattern[str]]):
    if not matching:
        return
    for sub in path.glob("*"):
        if not matching.match(sub.name):
            shutil.rmtree(sub)


def _should_extract(
        member: tarfile.TarInfo,
        matching: Optional[Pattern[str]] = None,
        mappings: Optional[dict[str, str]] = None) -> bool:
    return bool(
        (matching and matching.match(member.name))
        or (member.name in (mappings or {})))


# Packing

def pack(
        path: str | pathlib.Path,
        out: str | pathlib.Path,
        include: Optional[Pattern[str]] = None) -> None:
    (_pack_zst(path, out, include=include)
     if str(out).endswith(".zst")
     else _pack(path, out, include=include))


def _pack(
        path: str | pathlib.Path,
        out: str | pathlib.Path,
        include: Optional[Pattern[str]] = None) -> None:
    with tarfile.open(out, mode=tar_mode(out, mode="w")) as tar:
        tar.add(_prune(path, include), arcname=".")


def _pack_zst(
        path: str | pathlib.Path,
        out: str | pathlib.Path,
        include: Optional[Pattern[str]] = None) -> None:
    tarout = io.BytesIO()
    cctx = zstandard.ZstdCompressor(threads=-1)
    with tarfile.open(fileobj=tarout, mode="w") as tar:
        tar.add(_prune(path, include), arcname=".")
        tarout.seek(0)
        with open(out, "wb") as writeout:
            cctx.copy_stream(tarout, writeout)


def _prune(
        path: str | pathlib.Path,
        include: Optional[Pattern[str]] = None) -> pathlib.Path:
    path = pathlib.Path(path)
    if not include:
        return path
    for sub in path.glob("*"):
        if not include.match(sub.name):
            (shutil.rmtree(sub)
             if sub.is_dir()
             else sub.unlink())
    return path


# Repacking

@contextlib.contextmanager
def repack(
        out: str | pathlib.Path,
        *paths: str | pathlib.Path,
        matching: Optional[Pattern[str]] = None,
        mappings: Optional[dict[str, str]] = None,
        include: Optional[Pattern[str]] = None) -> Iterator[pathlib.Path]:
    with untar(*paths, matching=matching, mappings=mappings) as tardir:
        yield tardir
        pack(tardir, out, include=include)
