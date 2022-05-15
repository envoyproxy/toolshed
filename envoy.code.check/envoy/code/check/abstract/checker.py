"""Abstract code checker."""

import abc
import argparse
import pathlib
import re
from functools import cached_property
from typing import Dict, Mapping, Optional, Pattern, Set, Tuple, Type

import abstracts

from aio.core import directory as _directory, event, subprocess
from aio.core.tasks import inflate
from aio.run import checker

from envoy.base.utils import IProject
from envoy.code.check import abstract, typing


# TODO: Add a README in envoy repo with info on how to fix and maybe use
#   a template
GLINT_ADVICE = (
    "Glint check failed\n"
    "\n"
    "  Please fix your editor to ensure:\n"
    "\n"
    "      - no trailing whitespace\n"
    "      - no preceding mixed tabs/spaces\n"
    "      - all files end with a newline")

# This is excluding at least some of the things that `.gitignore` would.
GREP_EXCLUDE_GLOBS = (r"\#*", r"\.#*", r"*~")
GREP_EXCLUDE_DIR_GLOBS = (r"build", r"build*", r"generated", r"\.*", r"src")

NO_EXTENSIONS_ERROR_MSG = (
    "`--extensions_build_config` not provided, disabling extensions checks")


class CodeCheckerSummary(checker.CheckerSummary):

    def print_summary(self) -> None:
        """Write summary to stderr."""
        super().print_summary()
        if "glint" in self.checker.errors:
            self.writer_for("error")(GLINT_ADVICE)


@abstracts.implementer(event.IReactive)
class ACodeChecker(
        checker.Checker,
        event.AReactive,
        metaclass=abstracts.Abstraction):
    """Code checker."""

    checks = (
        "changelog",
        "extensions_fuzzed",
        "extensions_metadata",
        "extensions_registered",
        "glint",
        "python_yapf",
        "python_flake8",
        "shellcheck")

    @property
    def all_files(self) -> bool:
        return self.args.all_files

    @cached_property
    def disabled_checks(self):
        disabled = {}
        if not self.args.extensions_build_config:
            disabled["extensions_fuzzed"] = NO_EXTENSIONS_ERROR_MSG
            disabled["extensions_metadata"] = NO_EXTENSIONS_ERROR_MSG
            disabled["extensions_registered"] = NO_EXTENSIONS_ERROR_MSG
        return disabled

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
    def changelog(self) -> "abstract.AChangelogCheck":
        """Changelog checker."""
        return self.changelog_class(
            self.project,
            self.directory,
            **self.check_kwargs)

    @property  # type:ignore
    @abstracts.interfacemethod
    def changelog_class(self) -> Type["abstract.AChangelogCheck"]:
        raise NotImplementedError

    @property
    def check_kwargs(self) -> Mapping:
        return dict(
            fix=self.fix,
            loop=self.loop,
            pool=self.pool)

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
            exclude_dirs=self.exclude_dirs_from_grep,
            pool=self.pool,
            loop=self.loop)
        if not self.all_files:
            kwargs["changed"] = self.changed_since
        return kwargs

    @cached_property
    def extensions(self) -> "abstract.AExtensionsCheck":
        """Extensions checker."""
        return self.extensions_class(
            self.directory,
            extensions_build_config=self.args.extensions_build_config,
            **self.check_kwargs)

    @property  # type:ignore
    @abstracts.interfacemethod
    def extensions_class(self) -> Type["abstract.AExtensionsCheck"]:
        raise NotImplementedError

    @cached_property
    def flake8(self) -> "abstract.AFlake8Check":
        """Flake8 checker."""
        return self.flake8_class(self.directory, **self.check_kwargs)

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

    @cached_property
    def glint(self) -> "abstract.AGlintCheck":
        """Glint checker."""
        return self.glint_class(self.directory, **self.check_kwargs)

    @property  # type:ignore
    @abstracts.interfacemethod
    def glint_class(self) -> Type["abstract.AGlintCheck"]:
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
    def project(self) -> IProject:
        return self.project_class(self.path)

    @property  # type:ignore
    @abstracts.interfacemethod
    def project_class(self) -> Type[IProject]:
        raise NotImplementedError

    @cached_property
    def shellcheck(self) -> "abstract.AShellcheckCheck":
        """Shellcheck checker."""
        return self.shellcheck_class(self.directory, **self.check_kwargs)

    @property  # type:ignore
    @abstracts.interfacemethod
    def shellcheck_class(self) -> Type["abstract.AShellcheckCheck"]:
        raise NotImplementedError

    @property
    def summary_class(self) -> Type[CodeCheckerSummary]:
        """CodeChecker's summary class."""
        return CodeCheckerSummary

    @cached_property
    def yapf(self) -> "abstract.AYapfCheck":
        """YAPF checker."""
        return self.yapf_class(self.directory, **self.check_kwargs)

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
        parser.add_argument("--extensions_build_config")

    async def check_changelog(self):
        for changelog in self.changelog:
            errors = await changelog.errors
            if errors:
                self.error("changelog", errors)
            else:
                self.succeed(
                    "changelog",
                    [f"{changelog.version}"])

    async def check_extensions_fuzzed(self) -> None:
        """Check for glint issues."""
        if self.extensions.all_fuzzed:
            self.succeed(
                "extensions_fuzzed",
                ["All network filters are fuzzed"])
        else:
            self.error(
                "extensions_fuzzed",
                ["Check that all network filters robust against untrusted "
                 "downstreams are fuzzed by adding them to filterNames() "
                 f"in {self.extensions.fuzz_test_path}"])

    async def check_extensions_metadata(self) -> None:
        """Check for glint issues."""
        for extension, errors in self.extensions.metadata_errors.items():
            if errors:
                self.error("extensions_metadata", errors)
            else:
                self.succeed("extensions_metadata", [f"{extension}"])

    async def check_extensions_registered(self) -> None:
        """Check for glint issues."""
        errors = self.extensions.registration_errors
        if errors:
            self.error("extensions_registered", errors)
        else:
            self.succeed(
                "extensions_registered",
                ["Registered metadata matches found extensions"])

    async def check_glint(self) -> None:
        """Check for glint issues."""
        await self._code_check(self.glint)

    # TODO: catch errors in checkers as well as preloaders
    async def check_python_flake8(self) -> None:
        """Check for flake8 issues."""
        await self._code_check(self.flake8)

    async def check_python_yapf(self) -> None:
        """Check for yapf issues."""
        await self._code_check(self.yapf)

    async def check_shellcheck(self) -> None:
        """Check for shellcheck issues."""
        await self._code_check(self.shellcheck)

    @checker.preload(when=["changelog"])
    async def preload_changelog(self) -> None:
        preloader = inflate(
            self.changelog,
            lambda c: (c.errors, ))
        async for changelog in preloader:
            self.log.debug(f"Preloaded changelog: {changelog.version}")

    @checker.preload(
        when=["python_flake8"],
        catches=[subprocess.exceptions.OSCommandError])
    async def preload_flake8(self) -> None:
        await self.flake8.problem_files

    @checker.preload(
        when=["glint"],
        catches=[subprocess.exceptions.OSCommandError])
    async def preload_glint(self) -> None:
        await self.glint.problem_files

    @checker.preload(
        when=["shellcheck"],
        catches=[subprocess.exceptions.OSCommandError])
    async def preload_shellcheck(self) -> None:
        await self.shellcheck.problem_files

    @checker.preload(
        when=["python_yapf"],
        catches=[subprocess.exceptions.OSCommandError])
    async def preload_yapf(self) -> None:
        await self.yapf.problem_files

    def _check_output(
            self,
            check_files: Set[str],
            problem_files: typing.ProblemDict) -> None:
        # This can be slow/blocking for large result sets, run
        # in a separate thread
        for path in sorted(check_files):
            if path in problem_files:
                self.error(
                    self.active_check,
                    problem_files[path])
            else:
                self.succeed(
                    self.active_check,
                    [path])

    async def _code_check(self, check: "abstract.AFileCodeCheck") -> None:
        await self.loop.run_in_executor(
            None,
            self._check_output,
            await check.files,
            await check.problem_files)

    def _grep_re(self, arg: Optional[str]) -> Optional[Pattern[str]]:
        # When using system `grep` we want to filter out at least some
        # of the files that .gitignore would.
        # TODO: use globs on cli and covert to re here
        return (
            re.compile("|".join(arg))
            if arg
            else None)
