"""Abstract code checker."""

import abc
import argparse
import pathlib
import re
from functools import cached_property
from typing import Dict, Optional, Pattern, Tuple, Type

import abstracts

from aio.core import directory as _directory
from aio.run import checker

from envoy.code.check import abstract


# This is excluding at least some of the things that `.gitignore` would.
GREP_EXCLUDE_GLOBS = (r"\#*", r"\.#*", r"*~")
GREP_EXCLUDE_DIR_GLOBS = (r"build", r"build*", r"generated", r"\.*", r"src")


class ACodeChecker(
        checker.Checker,
        metaclass=abstracts.Abstraction):
    """Code checker."""

    checks = ("python_yapf", "python_flake8", "spelling", "spelling_dictionary")

    @property
    def all_files(self) -> bool:
        return self.args.all_files

    @property
    def exclude_from_grep(self) -> Tuple[str, ...]:
        """Globs to exclude when grepping, ignored if `git grep` is used."""
        return GREP_EXCLUDE_GLOBS if self.all_files else ()

    @property
    def exclude_dirs_from_grep(self) -> Tuple[str, ...]:
        """Glob directories to exclude when grepping, ignored if `git grep` is
        used."""
        return GREP_EXCLUDE_DIR_GLOBS if self.all_files else ()

    @property
    def changed_since(self) -> Optional[str]:
        return self.args.since

    @cached_property
    def directory(self) -> "_directory.ADirectory":
        """Greppable directory - optionally in a git repo, depending on whether
        we want to look at all files.
        """
        return self.directory_class(self.path, **self.directory_kwargs)

    @property
    def directory_class(self) -> Type["_directory.ADirectory"]:
        return (
            self.fs_directory_class
            if self.all_files
            else self.git_directory_class)

    @property
    def directory_kwargs(self) -> Dict:
        kwargs: Dict = dict(
            exclude_matcher=self.grep_excluding_re,
            path_matcher=self.grep_matching_re,
            exclude=self.exclude_from_grep,
            exclude_dirs=self.exclude_dirs_from_grep)
        if not self.all_files:
            kwargs["changed"] = self.changed_since
        return kwargs

    @cached_property
    def flake8(self) -> "abstract.AFlake8Check":
        """Flake8 checker."""
        return self.flake8_class(self.directory, fix=self.fix)

    @property  # type:ignore
    @abstracts.interfacemethod
    def flake8_class(self) -> Type["abstract.AFlake8Check"]:
        raise NotImplementedError

    @property  # type:ignore
    @abstracts.interfacemethod
    def fs_directory_class(self) -> Type["_directory.ADirectory"]:
        raise NotImplementedError

    @property  # type:ignore
    @abstracts.interfacemethod
    def git_directory_class(self) -> Type["_directory.AGitDirectory"]:
        raise NotImplementedError

    @property
    def grep_excluding_re(self) -> Optional[Pattern[str]]:
        return self._grep_re(self.args.excluding)

    @property
    def grep_matching_re(self) -> Optional[Pattern[str]]:
        return self._grep_re(self.args.matching)

    @property
    @abc.abstractmethod
    def path(self) -> pathlib.Path:
        return super().path

    @cached_property
    def spelling(self) -> "abstract.ASpellingCheck":
        """SPELLING checker."""
        return self.spelling_class(self.directory, fix=self.fix)

    @property  # type:ignore
    @abstracts.interfacemethod
    def spelling_class(self) -> Type["abstract.ASpellingCheck"]:
        raise NotImplementedError

    @cached_property
    def spelling_dictionary(self) -> "abstract.ASpellingDictionaryCheck":
        """Spelling dictionary checker."""
        return self.spelling_class(self.directory, fix=self.fix)

    @property  # type:ignore
    @abstracts.interfacemethod
    def spelling_dictionary_class(self) -> Type["abstract.ASpellingDictionaryCheck"]:
        raise NotImplementedError

    @cached_property
    def yapf(self) -> "abstract.AYapfCheck":
        """YAPF checker."""
        return self.yapf_class(self.directory, fix=self.fix)

    @property  # type:ignore
    @abstracts.interfacemethod
    def yapf_class(self) -> Type["abstract.AYapfCheck"]:
        raise NotImplementedError

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        super().add_arguments(parser)
        parser.add_argument("-a", "--all_files", action="store_true")
        parser.add_argument("-m", "--matching", action="append")
        parser.add_argument("-x", "--excluding", action="append")
        parser.add_argument("-s", "--since")

    async def check_python_flake8(self) -> None:
        """Check for flake8 issues."""
        await self._code_check(self.flake8)

    async def check_python_yapf(self) -> None:
        """Check for yapf issues."""
        await self._code_check(self.yapf)

    async def check_spelling(self) -> None:
        """Check for yapf issues."""
        await self._code_check(self.spelling)

    async def check_spelling_dictionary(self) -> None:
        """Check for yapf issues."""
        await self._code_check(self.spelling_dictionary)

    @checker.preload(
        when=["python_flake8"])
    async def preload_flake8(self) -> None:
        await self.flake8.problem_files

    @checker.preload(
        when=["python_yapf"])
    async def preload_yapf(self) -> None:
        await self.yapf.problem_files

    @checker.preload(
        when=["spelling"])
    async def preload_spelling(self) -> None:
        await self.spelling.problem_files

    async def _code_check(self, check: "abstract.ACodeCheck") -> None:
        problem_files = await check.problem_files
        for path in sorted(await check.files):
            if path in problem_files:
                self.error(
                    self.active_check,
                    problem_files[path])
            else:
                self.succeed(
                    self.active_check,
                    [f"🗸 {path}"])

    def _grep_re(self, arg: Optional[str]) -> Optional[Pattern[str]]:
        # When using system `grep` we want to filter out at least some
        # of the files that .gitignore would.
        # TODO: use globs on cli and covert to re here
        return (
            re.compile("|".join(arg))
            if arg
            else None)
