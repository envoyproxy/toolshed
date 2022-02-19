
import os
import pathlib
from functools import cached_property, lru_cache
from typing import Dict, List, Set, Tuple

from flake8.main.application import (  # type:ignore
    Application as Flake8Application)
from flake8 import (  # type:ignore
    utils as flake8_utils,
    checker as flake8_checker)

import abstracts

from aio.core.functional import async_property, threaded

from envoy.code.check import abstract


FLAKE8_CONFIG = '.flake8'


class Flake8App:
    """Wrapper around `flake8.main.application.Application`

    Provides optimized file discovery using app's lookup tools.
    """

    def __init__(self, path: str, args) -> None:
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

    def run_checks(self, paths):
        """Run flake8 checks."""
        self.app.run_checks(files=paths)
        self.app.report()

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

    @async_property
    async def checker_files(self) -> Set[str]:
        return set(
            path
            for path
            in await self.directory.files
            if self.flake8.include_file(path))

    @async_property
    async def errors(self) -> Dict[str, List[str]]:
        """Discovered flake8 errors."""
        await threaded(
            self.flake8.run_checks,
            await self.absolute_paths,
            stdout=self._handle_error)
        return self._errors

    @cached_property
    def flake8(self) -> Flake8App:
        """Wrapped flake8 application."""
        return Flake8App(
            str(self.directory.path),
            self.flake8_args)

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

    @async_property(cache=True)
    async def problem_files(self) -> Dict[str, List[str]]:
        """Discovered files with flake8 errors."""
        return (
            await self.errors
            if await self.files
            else {})

    @cached_property
    def _errors(self) -> Dict:
        return {}

    async def _handle_error(self, output):
        message = str(output)
        if not message:
            return
        path = self.directory.relative_path(message.split(":")[0])
        self._errors[path] = self._errors.get(path, [])
        self._errors[path].append(f"{path}: {message.split(':', 1)[1]}")
