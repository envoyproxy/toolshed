
import io
import os
import pathlib
from functools import cached_property, lru_cache
from typing import List, Set, Tuple

from flake8.main.application import Application  # type:ignore
from flake8 import (  # type:ignore
    utils as flake8_utils,
    checker as flake8_checker)

import abstracts

from aio.core.functional import async_property
from aio.core.functional import directory_context  # type:ignore

from envoy.code.check import abstract, typing


FLAKE8_CONFIG = '.flake8'


class Flake8Application(Application):
    """Subclassed flake8.Application to capture output."""

    @cached_property
    def output_fd(self) -> io.StringIO:
        return io.StringIO()

    def make_formatter(self) -> None:
        # ~Hacky workaround to capture flake8 output
        super().make_formatter()
        self.formatter.output_fd = self.output_fd
        self._formatter_stop = self.formatter.stop
        self.formatter.stop = self._stop

    def _stop(self) -> None:
        self.output_fd.seek(0)
        self._results: List[str] = [
            x
            for x
            in self.output_fd.read().strip().split("\n")
            if x]
        self._formatter_stop()


class Flake8App:
    """Wrapper around `flake8.main.application.Application`

    Provides optimized file discovery using app's lookup tools.
    """

    def __init__(self, path: str, args: Tuple[str, ...]) -> None:
        self.path = path
        self.args = args

    @cached_property
    def app(self) -> Flake8Application:
        flake8_app = Flake8Application()
        flake8_app.initialize(self.args)
        return flake8_app

    @property
    def manager(self) -> flake8_checker.Manager:
        """Flake8 file checker manager."""
        return self.app.file_checker_manager

    def include_file(self, path: str) -> bool:
        """Include file according to flake8 config."""
        path = os.path.join(self.path, path)
        return (
            self._filename_matches(path)
            and self._include_directory(os.path.dirname(path))
            and not self._is_excluded(path))

    def include_files(self, files: Set[str]) -> Set[str]:
        return set(
            path
            for path
            in files
            if self.include_file(os.path.join(self.path, path)))

    def run_checks(self, paths: Set[str]) -> List[str]:
        """Run flake8 checks."""
        with directory_context(self.path):
            self.app.run_checks(files=paths)
            self.app.report()
        return self.app._results

    @cached_property
    def _excluded_paths(self) -> Set[str]:
        return set()

    def _filename_matches(self, path: str) -> bool:
        return flake8_utils.fnmatch(
            path,
            self.app.options.filename)

    @lru_cache
    def _include_directory(self, path: str) -> bool:
        while True:
            if path == self.path:
                return True
            if not self._include_path(path):
                return False
            path = os.path.dirname(path)

    @lru_cache
    def _include_path(self, path: str) -> bool:
        exclude = (
           any(path.startswith(x) for x in self._excluded_paths)
           or self._is_excluded(path))
        if exclude:
            self._excluded_paths.add(path)
        return not exclude

    def _is_excluded(self, path: str) -> bool:
        return self.manager.is_path_excluded(path)


class AFlake8Check(abstract.ACodeCheck, metaclass=abstracts.Abstraction):
    """Flake8 check for a fileset."""

    @classmethod
    def check_flake8_files(
            cls,
            path: str,
            args: Tuple[str, ...],
            files: Set[str]):
        return Flake8App(
            path,
            args).run_checks(files)

    @classmethod
    def filter_flake8_files(
            cls,
            path: str,
            args: Tuple[str, ...],
            files: Set[str]):
        return Flake8App(
            path,
            args).include_files(files)

    @async_property
    async def checker_files(self) -> Set[str]:
        return await self.execute(
            self.filter_flake8_files,
            self.directory.absolute_path,
            self.flake8_args,
            await self.directory.files)

    @property
    def flake8_args(self) -> Tuple[str, ...]:
        """Flake configuration args."""
        return (
            "--config",
            str(self.flake8_config_path),
            str(self.directory.path))

    @property
    def flake8_config_path(self) -> pathlib.Path:
        """Path to flake8 configuration."""
        return self.directory.path.joinpath(FLAKE8_CONFIG)

    @async_property
    async def flake8_errors(self) -> List[str]:
        return await self.execute(
            self.check_flake8_files,
            self.directory.absolute_path,
            self.flake8_args,
            await self.files)

    @async_property(cache=True)
    async def problem_files(self) -> typing.ProblemDict:
        """Discovered flake8 errors."""
        return self.handle_errors(await self.flake8_errors)

    def handle_errors(self, errors: List[str]) -> typing.ProblemDict:
        flake8_errors: typing.ProblemDict = {}
        for error in errors:
            path, message = self._parse_error(error)
            flake8_errors[path] = flake8_errors.get(path, [])
            flake8_errors[path].append(message)
        return flake8_errors

    def _parse_error(self, error: str) -> Tuple[str, str]:
        path = error.split(":")[0]
        return (
            path,
            f"{path}: {error.split(':', 1)[1]}")
