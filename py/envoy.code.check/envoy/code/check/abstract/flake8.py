
import io
import logging
import os
import pathlib
from functools import cached_property, lru_cache

from flake8.main.application import Application  # type:ignore
from flake8 import (  # type:ignore
    utils as flake8_utils,
    checker as flake8_checker)

import abstracts

from aio.core.functional import async_property
from aio.core.directory.utils import directory_context
from aio.run import checker

from envoy.code.check import abstract, interface, typing


FLAKE8_CONFIG = '.flake8'


# Workaround for https://github.com/PyCQA/flake8/issues/1390
# logging.getLogger("flake8.options.manager").setLevel(logging.ERROR)
logger = logging.getLogger(__name__)


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
        self._results: list[str] = [
            x
            for x
            in self.output_fd.read().strip().split("\n")
            if x]
        self._formatter_stop()


class Flake8App:
    """Wrapper around `flake8.main.application.Application`

    Provides optimized file discovery using app's lookup tools.
    """

    def __init__(self, path: str, args: tuple[str, ...]) -> None:
        self.path = path
        self.args = args

    @cached_property
    def app(self) -> Flake8Application:
        """Flake8 Application."""
        flake8_app = Flake8Application()
        flake8_app.initialize(self.args)
        return flake8_app

    @property
    def exclude(self) -> list[str]:
        return self.manager.options.exclude

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

    def include_files(self, files: set[str]) -> set[str]:
        """Figure out whether to include a file for checking."""
        return set(
            path
            for path
            in files
            if self.include_file(os.path.join(self.path, path)))

    def run_checks(self, paths: set[str]) -> list[str]:
        """Run flake8 checks."""
        with directory_context(self.path):
            self.app.options.filenames = paths
            self.app.file_checker_manager.start()
            self.app.run_checks()
            self.app.report()
        return self.app._results

    @cached_property
    def _excluded_paths(self) -> set[str]:
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
        if not self.exclude:
            return False
        basename = os.path.basename(path)
        if flake8_utils.fnmatch(basename, self.exclude):
            logger.debug(f'"{basename}" has been excluded')
            return True

        absolute_path = os.path.abspath(path)
        match = flake8_utils.fnmatch(absolute_path, self.exclude)
        logger.debug(
            f'"{absolute_path}" has {"" if match else "not "}been excluded')
        return match


@abstracts.implementer(interface.IFlake8Check)
class AFlake8Check(abstract.AFileCodeCheck, metaclass=abstracts.Abstraction):
    """Flake8 check for a fileset."""

    @classmethod
    def check_flake8_files(
            cls,
            path: str,
            args: tuple[str, ...],
            files: set[str]) -> list[str]:
        """Flake8 checker."""
        return Flake8App(
            path,
            args).run_checks(files)

    @classmethod
    def filter_flake8_files(
            cls,
            path: str,
            args: tuple[str, ...],
            files: set[str]) -> set[str]:
        """Flake8 file discovery."""
        return Flake8App(
            path,
            args).include_files(files)

    @async_property
    async def checker_files(self) -> set[str]:
        return await self.execute(
            self.filter_flake8_files,
            self.directory.absolute_path,
            self.flake8_args,
            await self.directory.files)

    @property
    def flake8_args(self) -> tuple[str, ...]:
        """Flake configuration args."""
        return (
            "--color=never",
            "--config",
            str(self.flake8_config_path),
            str(self.directory.path))

    @property
    def flake8_config_path(self) -> pathlib.Path:
        """Path to flake8 configuration."""
        return self.directory.path.joinpath(FLAKE8_CONFIG)

    @async_property
    async def flake8_errors(self) -> list[str]:
        """Flake8 error list for check files."""
        # Important dont send an empty set to the flake8 checker,
        # as flake8 will check every file in path.
        return (
            await self.execute(
                self.check_flake8_files,
                self.directory.absolute_path,
                self.flake8_args,
                await self.files)
            if await self.files
            else [])

    @async_property(cache=True)
    async def problem_files(self) -> typing.ProblemDict:
        """Discovered flake8 errors."""
        return self.handle_errors(await self.flake8_errors)

    def handle_errors(self, errors: list[str]) -> typing.ProblemDict:
        """Turn flake8 error list -> `ProblemDict`."""
        flake8_errors: dict[str, list[str]] = {}
        for error in errors:
            path, message = self._parse_error(error)
            flake8_errors[path] = flake8_errors.get(path, [])
            flake8_errors[path].append(message)
        return {
            p: checker.Problems(errors=errors)
            for p, errors
            in flake8_errors.items()}

    def _parse_error(self, error: str) -> tuple[str, str]:
        path = error.split(":")[0]
        return (
            path,
            f"{path}: {error.split(':', 1)[1]}")
